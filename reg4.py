import os
import tkinter as tk
from tkinter import messagebox, ttk
import sqlite3
import datetime
from datetime import timedelta
import hashlib
import re
import requests

DEFAULT_PRODUCT_NAMES = [
    "PIENS", "MAIZE", "DESA", "SIERS", "OLAS",
    "MALTĀ GAĻA", "VISTAS FILEJA", "PELMEŅI", "SĀLS", "CUKURS", "CITS"
]

def init_db():
    conn = sqlite3.connect('produkti.db')
    cursor = conn.cursor()
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS Users ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "username TEXT UNIQUE, "
        "password TEXT)"
    )
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS Inventory ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "user_id INTEGER, "
        "name TEXT, "
        "category TEXT, "
        "quantity INTEGER, "
        "exp_date DATE, "
        "FOREIGN KEY(user_id) REFERENCES Users(id))"
    )
    conn.commit()
    conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def center_window(window, width, height):
    window.update_idletasks()
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    x = (screen_width // 2) - (width // 2)
    y = (screen_height // 2) - (height // 2)
    window.geometry(f'{width}x{height}+{x}+{y}')

def is_valid_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Pārtikas produktu reģistrs")
        self.width = 900
        self.height = 600
        center_window(self, self.width, self.height)
        self.minsize(850, 550)
        
        self.current_user_id = None
        self.current_username = None
        
        container = tk.Frame(self)
        container.pack(side="top", fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        for F in (LoginFrame, SignUpFrame, MainFrame):
            frame = F(container, self)
            self.frames[F] = frame
            frame.grid(row=0, column=0, sticky="nsew")
            
        self.show_frame(LoginFrame)

    def show_frame(self, cont):
        frame = self.frames[cont]
        frame.tkraise()
        if cont == MainFrame:
            frame.load_data()
            if not getattr(frame, 'warnings_shown', False):
                frame.check_warnings()
                frame.warnings_shown = True

class LoginFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        content = tk.Frame(self)
        content.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(content, text="PIETEIKŠANĀS", font=("Arial", 18, "bold")).pack(pady=20) 
        tk.Label(content, text="LIETOTĀJVĀRDS", font=("Arial", 10)).pack(anchor="w")
        self.entry_user = tk.Entry(content, width=35, font=("Arial", 11))
        self.entry_user.pack(pady=10)
        tk.Label(content, text="PAROLE", font=("Arial", 10)).pack(anchor="w")
        self.entry_pass = tk.Entry(content, show="*", width=35, font=("Arial", 11))
        self.entry_pass.pack(pady=10)
        tk.Button(content, text="IEIET SISTĒMĀ", bg="#4CAF50", fg="white", font=("Arial", 10, "bold"),
                  command=self.login, width=25, pady=10).pack(pady=20)
        tk.Button(content, text="Nav konta? Reģistrēties šeit", font=("Arial", 9, "underline"),
                  command=lambda: controller.show_frame(SignUpFrame), borderwidth=0, cursor="hand2").pack()

    def login(self):
        user = self.entry_user.get().strip()
        pwd = hash_password(self.entry_pass.get())
        with sqlite3.connect('produkti.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM Users WHERE username=? AND password=?", (user, pwd))
            result = cursor.fetchone()
        if result:
            self.controller.current_user_id = result[0]
            self.controller.current_username = user
            self.controller.show_frame(MainFrame)
        else:
            messagebox.showerror("Kļūda", "Nepareizs lietotājvārds vai parole!")

class SignUpFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        content = tk.Frame(self)
        content.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(content, text="REĢISTRĀCIJA", font=("Arial", 16, "bold")).pack(pady=20) 
        tk.Label(content, text="LIETOTĀJVĀRDS").pack()
        self.entry_user = tk.Entry(content, width=35); self.entry_user.pack(pady=5)
        tk.Label(content, text="PAROLE").pack()
        self.entry_pass = tk.Entry(content, show="*", width=35); self.entry_pass.pack(pady=5)
        tk.Label(content, text="APSTIPRINĀT PAROLI").pack()
        self.entry_pass_conf = tk.Entry(content, show="*", width=35); self.entry_pass_conf.pack(pady=5)
        tk.Button(content, text="REĢISTRĒTIES", bg="#2196F3", fg="white", 
                  command=self.signup, width=25, pady=10).pack(pady=15)
        tk.Button(content, text="Atpakaļ uz pieteikšanos", command=lambda: controller.show_frame(LoginFrame), borderwidth=0).pack()

    def signup(self):
        user = self.entry_user.get().strip()
        pwd = self.entry_pass.get().strip()
        pwd2 = self.entry_pass_conf.get().strip()
        if not user or not pwd or not pwd2:
            messagebox.showwarning("Brīdinājums", "Visi lauki ir obligāti!")
            return
        if pwd != pwd2:
            messagebox.showerror("Kļūda", "Paroles nesakrīt!")
            return
        try:
            with sqlite3.connect('produkti.db') as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO Users (username, password) VALUES (?,?)", (user, hash_password(pwd)))
            messagebox.showinfo("Veiksmīgi", "Konts izveidots! Tagad vari pieteikties.")
            self.controller.show_frame(LoginFrame)
        except:
            messagebox.showerror("Kļūda", "Šāds lietotājvārds jau eksistē!")

class MainFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        self.title_label = tk.Label(self, text="", font=("Arial", 16, "bold"))
        self.title_label.pack(pady=15)

        style = ttk.Style()
        style.configure("Treeview", rowheight=70, font=("Arial", 11))
        
        btn_frame = tk.Frame(self, padx=20)
        btn_frame.pack(fill="x", pady=10)
        tk.Button(btn_frame, text="+ PIEVIENOT", bg="#4CAF50", fg="white", command=self.open_add_window).pack(side="left", padx=5)
        tk.Button(btn_frame, text="✎ REDIĢĒT", bg="#2196F3", fg="white", command=self.open_edit_window).pack(side="left", padx=5)
        tk.Button(btn_frame, text="- DZĒST", bg="#f44336", fg="white", command=self.delete_product).pack(side="left", padx=5)
        tk.Button(btn_frame, text="ZIŅOT PAR KĻŪDU", bg="#808080", fg="white", command=lambda: ErrorReportWindow(self)).pack(side="right")

        base_path = os.path.dirname(__file__)
        self.status_smile = tk.PhotoImage(file=os.path.join(base_path, "smile.png")).subsample(3, 3)
        self.status_neutral = tk.PhotoImage(file=os.path.join(base_path, "neutral_face.png")).subsample(3, 3)
        self.status_sad = tk.PhotoImage(file=os.path.join(base_path, "white_frowning_face.png")).subsample(3, 3)
        self.status_unknown = self.status_neutral

        columns = ("name", "qty", "exp", "type")
        self.tree = ttk.Treeview(self, columns=columns, show="tree headings")
        self.tree.heading("#0", text="STATUSS")
        self.tree.column("#0", width=120, anchor="center", stretch=False)
        self.tree.tag_configure('status_good', background='#d9f2d9')
        self.tree.tag_configure('status_warning', background='#fff8c6')
        self.tree.tag_configure('status_bad', background='#f8d0d4')
        self.tree.tag_configure('status_unknown', background='#e8e8e8')

        for col, text in (("name", "PRODUKTS"), ("qty", "SKAITS"), ("exp", "TERMIŅŠ"), ("type", "VIETA")):
            self.tree.heading(col, text=text, command=lambda c=col: self.sort_column(c, False))

        self.tree.pack(fill="both", expand=True, padx=20, pady=20)

    def load_data(self):
        self.tree.delete(*self.tree.get_children())
        today = datetime.date.today()
        three_days_later = today + timedelta(days=3)
        with sqlite3.connect('produkti.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, quantity, exp_date, category FROM Inventory WHERE user_id=?", (self.controller.current_user_id,))
            for item_id, name, qty, exp_date, category in cursor.fetchall():
                try:
                    exp_date_dt = datetime.datetime.strptime(exp_date, "%Y-%m-%d").date()
                    if exp_date_dt < today:
                        status_image, row_tag = self.status_sad, 'status_bad'
                    elif exp_date_dt <= three_days_later:
                        status_image, row_tag = self.status_neutral, 'status_warning'
                    else:
                        status_image, row_tag = self.status_smile, 'status_good'
                except:
                    status_image, row_tag = self.status_unknown, 'status_unknown'

                self.tree.insert("", tk.END, iid=item_id, image=status_image,
                                 values=(name, qty, exp_date, category), tags=(row_tag,))
        self.update_title_label()

    def sort_column(self, col, reverse):
        data = [(self.tree.set(child, col), child) for child in self.tree.get_children('')]
        if col == "qty":
            data.sort(key=lambda x: int(x[0]), reverse=reverse)
        else:
            data.sort(reverse=reverse)
        for index, (val, child) in enumerate(data):
            self.tree.move(child, '', index)
        self.tree.heading(col, command=lambda: self.sort_column(col, not reverse))

    def open_add_window(self):
        AddProductWindow(self)

    def open_edit_window(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Brīdinājums", "Izvēlies produktu, kuru vēlies rediģēt.")
            return

        item_id = selected[0]
        with sqlite3.connect('produkti.db') as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name, quantity, exp_date, category FROM Inventory WHERE id=? AND user_id=?",
                (item_id, self.controller.current_user_id)
            )
            row = cursor.fetchone()

        if not row:
            messagebox.showerror("Kļūda", "Izvēlētais produkts netika atrasts.")
            return

        AddProductWindow(self, item_id=item_id, name=row[0], qty=row[1], exp=row[2], cat=row[3])

    def delete_product(self):
        selected = self.tree.selection()
        if selected:
            with sqlite3.connect('produkti.db') as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM Inventory WHERE id=?", (selected[0],))
            self.load_data()

    def update_title_label(self):
        username = self.controller.current_username or "Lietotāja"
        self.title_label.config(text=f"{username}'s produktu saraksts")

    def check_warnings(self):
        today = datetime.date.today()
        limit = today + timedelta(days=3)
        with sqlite3.connect('produkti.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name, exp_date FROM Inventory WHERE user_id=?", (self.controller.current_user_id,))
            for name, exp_date in cursor.fetchall():
                try:
                    exp_date_dt = datetime.datetime.strptime(exp_date, "%Y-%m-%d").date()
                    if exp_date_dt < today:
                        messagebox.showwarning("BRĪDINĀJUMS", f"{name} termiņš ir beidzies: {exp_date}")
                    elif exp_date_dt <= limit:
                        messagebox.showwarning("BRĪDINĀJUMS", f"{name} termiņš drīz beigsies: {exp_date}")
                except:
                    continue

class AddProductWindow(tk.Toplevel):
    def __init__(self, parent, item_id=None, name="", qty="", exp="", cat=""):
        super().__init__(parent)
        self.parent = parent
        self.item_id = item_id
        self.title("Rediģēt produktu" if item_id else "Pievienot produktu")
        center_window(self, 400, 500)
        container = tk.Frame(self, padx=30, pady=20)
        container.pack(fill="both", expand=True)
        self.transient(self.parent)
        self.grab_set()
        self.focus_force()

        tk.Label(container, text="PRODUKTA NOSAUKUMS").pack(anchor="w")
        self.name_var = tk.StringVar(value=name)
        self.name_var.trace_add("write", lambda *args: self.name_var.set(self.name_var.get().upper()))

        self.combo_name = ttk.Combobox(container, textvariable=self.name_var, font=("Arial", 11))
        self.combo_name['values'] = self.get_product_name_options()
        self.combo_name.pack(fill="x", pady=5)

        tk.Label(container, text="KATEGORIJA").pack(anchor="w", pady=(10,0))
        self.cat_var = tk.StringVar(value=cat)
        self.cat_var.trace_add("write", lambda *args: self.cat_var.set(self.cat_var.get().upper()))
        self.combo = ttk.Combobox(container, textvariable=self.cat_var, font=("Arial", 11))
        self.combo['values'] = ("LEDUSSKAPIS", "PLAUKTS", "SALDĒTAVA", "CITS")
        self.combo.pack(fill="x", pady=5)
        tk.Label(container, text="DAUDZUMS").pack(anchor="w", pady=(10,0))
        self.e_qty = tk.Entry(container, font=("Arial", 11))
        self.e_qty.pack(fill="x", pady=5)
        self.e_qty.insert(0, qty)
        tk.Label(container, text="TERMIŅŠ (GGGG-MM-DD)").pack(anchor="w", pady=(10,0))
        self.e_exp = tk.Entry(container, font=("Arial", 11))
        self.e_exp.pack(fill="x", pady=5)
        self.e_exp.insert(0, exp)
        tk.Button(container, text="SAGLABĀT", bg="#4CAF50", fg="white", pady=10, font=("Arial", 10, "bold"),
                  command=self.save_product).pack(fill="x", pady=20)
        tk.Button(container, text="ATCELT", bg="#AF4C4C", fg="white", pady=10, font=("Arial", 10, "bold"),
                  command=self.destroy).pack(fill="x", pady=5)

    def get_product_name_options(self):
        try:
            with sqlite3.connect('produkti.db') as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT DISTINCT name FROM Inventory WHERE user_id=?", (self.parent.controller.current_user_id,))
                existing = [row[0] for row in cursor.fetchall() if row[0]]
        except:
            existing = []
        options = []
        for prod in DEFAULT_PRODUCT_NAMES + existing:
            if prod not in options:
                options.append(prod)
        return options

    def save_product(self):
        if self._save_current_product():
            self.parent.load_data()
            self.destroy()

    def _save_current_product(self):
        name = self.name_var.get().strip().upper()
        qty = self.e_qty.get().strip()
        cat = self.cat_var.get().strip()
        exp = self.e_exp.get().strip()

        if not name or not qty or not cat:
            messagebox.showwarning("Brīdinājums", "Lūdzu, aizpildi visus laukus!")
            return False

        if not exp:
            with sqlite3.connect('produkti.db') as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT default_days FROM Default_Products WHERE name=?", (name,))
                res = cursor.fetchone()
                days = res[0] if res else 5
            exp = (datetime.date.today() + timedelta(days=days)).strftime("%Y-%m-%d")

        with sqlite3.connect('produkti.db') as conn:
            cursor = conn.cursor()
            if self.item_id:
                cursor.execute(
                    "UPDATE Inventory SET name=?, category=?, quantity=?, exp_date=? WHERE id=? AND user_id=?",
                    (name, cat, qty, exp, self.item_id, self.parent.controller.current_user_id)
                )
                messagebox.showinfo("Veiksmīgi", "Produkts veiksmīgi rediģēts!")
            else:
                cursor.execute("INSERT INTO Inventory (user_id, name, category, quantity, exp_date) VALUES (?,?,?,?,?)",
                               (self.parent.controller.current_user_id, name, cat, qty, exp))
                messagebox.showinfo("Veiksmīgi", "Produkts veiksmīgi pievienots!")
        return True

class ErrorReportWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Ziņot kļūdu")
        center_window(self, 450, 480)
        container = tk.Frame(self, padx=20, pady=20)
        container.pack(fill="both", expand=True)
        tk.Label(container, text="TAVS E-PASTS (obligāts):").pack(anchor="w")
        self.email_entry = tk.Entry(container, font=("Arial", 11), width=50) 
        self.email_entry.pack(fill="x", pady=10)
        tk.Label(container, text="KĻŪDAS APRAKSTS:").pack(anchor="w")
        self.text_area = tk.Text(container, height=10); self.text_area.pack(fill="both", expand=True, pady=10)
        tk.Button(container, text="SŪTĪT ZIŅOJUMU", bg="#2196F3", fg="white", pady=10,
                  command=self.submit_report).pack(fill="x")

    def submit_report(self):
        email = self.email_entry.get().strip()
        msg = self.text_area.get("1.0", tk.END).strip()
        if not is_valid_email(email) or not msg:
            messagebox.showwarning("Kļūda", "Aizpildiet e-pastu un aprakstu!")
            return
        try:
            requests.post("https://formspree.io/f/xeepnlrp", json={"email": email, "message": msg}, timeout=5)
            messagebox.showinfo("Paldies", "Ziņa nosūtīta!")
            self.destroy()
        except: messagebox.showerror("Kļūda", "Neizdevās nosūtīt!")

if __name__ == "__main__":
    init_db()
    app = App()
    app.mainloop()