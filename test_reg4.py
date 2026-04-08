import pytest
import sqlite3
import tkinter.messagebox
import tempfile
import os
from unittest.mock import patch, MagicMock
import tkinter as tk

# Import your application file. 
# Make sure your original file is named reg4.py
import reg4 

# ==========================================
# FIXTURES
# ==========================================

@pytest.fixture(autouse=True)
def mock_gui_elements(monkeypatch):
    monkeypatch.setattr('tkinter.Tk', MagicMock())
    monkeypatch.setattr('tkinter.PhotoImage', MagicMock())
    monkeypatch.setattr(reg4, 'center_window', lambda *args: None)

@pytest.fixture
def test_db(monkeypatch):
    # Create a temporary database file
    temp_fd, temp_path = tempfile.mkstemp(suffix='.db')
    os.close(temp_fd)  # Close the file descriptor, we'll use the path
    
    # Store the original connect function
    original_connect = sqlite3.connect
    
    # Patch sqlite3.connect so reg4.py uses our temporary database
    def mock_connect(*args, **kwargs):
        if args and args[0] == 'produkti.db':
            return original_connect(temp_path, *args[1:], **kwargs)
        else:
            return original_connect(*args, **kwargs)
    
    monkeypatch.setattr('sqlite3.connect', mock_connect)
    
    # Initialize the tables in our temporary database
    reg4.init_db()
    
    yield temp_path
    
    # Clean up the temporary file
    try:
        os.unlink(temp_path)
    except PermissionError:
        pass  # File might still be in use, but temp dir will clean it up

@pytest.fixture
def app(test_db):
    try:
        root = reg4.App()
        root.withdraw()  # Hide the main window during tests
        yield root
        root.destroy()
    except Exception as e:
        if "Tcl" in str(e) or "tk" in str(e).lower():
            pytest.skip(f"Tkinter not properly installed: {e}")
        else:
            raise

# ==========================================
# UTILITY TESTS
# ==========================================

def test_hash_password():
    # SHA-256 hash of "test1234"
    expected_hash = "937e8d5fbb48bd4949536cd65b8d35c426b80d2f830c5c308e2cdec422ae2244"
    assert reg4.hash_password("test1234") == expected_hash
    assert reg4.hash_password("test123") != reg4.hash_password("test1234")  

def test_is_valid_email():
    assert reg4.is_valid_email("user@example.com") is True
    assert reg4.is_valid_email("john.doe@domain.co.uk") is True
    assert reg4.is_valid_email("invalid-email") is False
    assert reg4.is_valid_email("user@.com") is False
    assert reg4.is_valid_email("@domain.com") is False

# ==========================================
# DATABASE TESTS
# ==========================================

def test_init_db(test_db):
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()
    
    # Check if the Users table was created
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Users'")
    assert cursor.fetchone() is not None
    
    # Check if the Inventory table was created
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Inventory'")
    assert cursor.fetchone() is not None
    
    conn.close()

# ==========================================
# GUI LOGIC TESTS (Authentication)
# ==========================================

def test_signup_success(app, monkeypatch, test_db):
    signup_frame = app.frames[reg4.SignUpFrame]
    
    # Simulate user input
    signup_frame.entry_user.insert(0, "new_user")
    signup_frame.entry_pass.insert(0, "securepass")
    signup_frame.entry_pass_conf.insert(0, "securepass")
    
    # Mock messagebox so it doesn't interrupt the test
    info_messages = []
    monkeypatch.setattr(tkinter.messagebox, 'showinfo', lambda title, msg: info_messages.append(title))
    
    # Trigger signup
    signup_frame.signup()
    
    # Verify success message was triggered
    assert "Veiksmīgi" in info_messages
    
    # Verify user was actually saved to the database
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM Users WHERE username=?", ("new_user",))
    result = cursor.fetchone()
    assert result and result[0] == "new_user"
    conn.close()

def test_signup_password_mismatch(app, monkeypatch):
    signup_frame = app.frames[reg4.SignUpFrame]
    
    signup_frame.entry_user.insert(0, "test_user")
    signup_frame.entry_pass.insert(0, "pass1")
    signup_frame.entry_pass_conf.insert(0, "pass2")  # Mismatch
    
    error_messages = []
    monkeypatch.setattr(tkinter.messagebox, 'showerror', lambda title, msg: error_messages.append(title))
    
    signup_frame.signup()
    assert "Kļūda" in error_messages

def test_login_success(app, monkeypatch, test_db):
    # Pre-populate database with a test user
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO Users (username, password) VALUES (?, ?)", 
                   ("login_user", reg4.hash_password("mypassword")))
    conn.commit()
    conn.close()
    
    login_frame = app.frames[reg4.LoginFrame]
    
    # Simulate user typing credentials
    login_frame.entry_user.insert(0, "login_user")
    login_frame.entry_pass.insert(0, "mypassword")
    
    # Track if the application navigates to the MainFrame
    frames_shown = []
    monkeypatch.setattr(app, 'show_frame', lambda frame: frames_shown.append(frame))
    
    login_frame.login()
    
    # Assertions
    assert app.current_username == "login_user"
    assert app.current_user_id == 1
    assert reg4.MainFrame in frames_shown

def test_login_failure(app, monkeypatch):
    login_frame = app.frames[reg4.LoginFrame]
    login_frame.entry_user.insert(0, "ghost_user")
    login_frame.entry_pass.insert(0, "wrongpass")
    
    errors = []
    monkeypatch.setattr(tkinter.messagebox, 'showerror', lambda title, msg: errors.append(title))
    
    login_frame.login()
    assert "Kļūda" in errors
    assert app.current_username is None

# ==========================================
# API / INTEGRATION TESTS
# ==========================================

@patch('reg4.requests.post')
def test_error_report_submission(mock_post, app, monkeypatch):
    # Instantiate the error reporting window
    report_window = reg4.ErrorReportWindow(app)
    
    # Fill in the form
    report_window.email_entry.insert(0, "test@example.com")
    report_window.text_area.insert("1.0", "The app is doing something weird.")
    
    # Mock messagebox to prevent popup
    monkeypatch.setattr(tkinter.messagebox, 'showinfo', lambda *args: None)
    
    # Click submit
    report_window.submit_report()
    
    # Verify requests.post was called correctly
    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    assert kwargs['json']['email'] == "test@example.com"
    assert kwargs['json']['message'] == "The app is doing something weird."
    assert kwargs['timeout'] == 5