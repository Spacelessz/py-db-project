import psycopg2
import tkinter as tk
from tkinter import ttk, messagebox

# ---------------------------- ПОДКЛЮЧЕНИЕ К БАЗЕ ----------------------------

def get_connection():
    return psycopg2.connect(
        dbname="project db",
        user="postgres",
        password="1234",
        host="localhost",
        port="5432"
    )

# ---------------------------- УТИЛИТЫ ДЛЯ КАТЕГОРИЙ ----------------------------

def get_categories():
    """Возвращает список кортежей (id, name) всех категорий"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM categories ORDER BY id")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def refresh_categories():
    """Обновляет глобальную переменную categories_list и Combobox, если он есть"""
    global categories_list, category_names
    categories_list = get_categories()
    category_names = [r[1] for r in categories_list]
    # если combobox существует — обновляем его значения
    try:
        combobox_category['values'] = category_names
    except NameError:
        pass

# ---------------------------- ФУНКЦИИ ДЛЯ БД ----------------------------

def load_materials():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT m.id, m.name, m.unit, m.quantity, COALESCE(c.name, '')
        FROM materials m
        LEFT JOIN categories c ON m.category_id = c.id
        ORDER BY m.id
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def add_category(name):
    if not name or name.strip() == "":
        raise ValueError("Имя категории не может быть пустым")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO categories (name) VALUES (%s) RETURNING id", (name.strip(),))
    new_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return new_id


def add_material(name, unit, quantity, min_quantity, category_id):
    if not name.strip():
        raise ValueError("Название материала не может быть пустым")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO materials (name, unit, quantity, min_quantity, category_id)
        VALUES (%s, %s, %s, %s, %s) RETURNING id
    """, (name.strip(), unit.strip(), quantity, min_quantity, category_id))
    new_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return new_id


def increase_material(material_id, amount):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE materials 
        SET quantity = quantity + %s
        WHERE id = %s
    """, (amount, material_id))

    cur.execute("""
        INSERT INTO transactions (material_id, type, amount, comment)
        VALUES (%s, 'приход', %s, 'Операция через программу')
    """, (material_id, amount))

    conn.commit()
    cur.close()
    conn.close()


def decrease_material(material_id, amount):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT quantity FROM materials WHERE id = %s", (material_id,))
    res = cur.fetchone()
    if res is None:
        cur.close()
        conn.close()
        raise ValueError("Материал с таким ID не найден")
    current_qty = res[0]

    if current_qty < amount:
        cur.close()
        conn.close()
        raise ValueError("Недостаточно материалов на складе!")

    cur.execute("""
        UPDATE materials 
        SET quantity = quantity - %s
        WHERE id = %s
    """, (amount, material_id))

    cur.execute("""
        INSERT INTO transactions (material_id, type, amount, comment)
        VALUES (%s, 'расход', %s, 'Операция через программу')
    """, (material_id, amount))

    conn.commit()
    cur.close()
    conn.close()


def load_transactions():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT t.id, COALESCE(m.name, ''), t.type, t.amount, COALESCE(t.comment, ''), t.operation_date
        FROM transactions t
        LEFT JOIN materials m ON t.material_id = m.id
        ORDER BY t.id DESC
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

# ---------------------------- GUI (TKINTER) ----------------------------

def refresh_table():
    for row in tree.get_children():
        tree.delete(row)
    for row in load_materials():
        tree.insert("", tk.END, values=row)


def add_category_window():
    win = tk.Toplevel(root)
    win.title("Добавить категорию")
    win.geometry("300x120")

    tk.Label(win, text="Название категории:").pack(pady=(10,0))
    entry = tk.Entry(win)
    entry.pack(padx=10, fill='x')

    def save():
        try:
            new_id = add_category(entry.get())
            refresh_categories()  # обновляем комбобокс категорий
            messagebox.showinfo("Успех", f"Категория добавлена (id={new_id})")
            win.destroy()
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    tk.Button(win, text="Сохранить", command=save).pack(pady=10)


def add_material_window():
    win = tk.Toplevel(root)
    win.title("Добавить материал")
    win.geometry("400x320")

    labels = ["Название", "Единица (шт, кг)", "Количество", "Мин. остаток", "Категория"]
    entries = []

    tk.Label(win, text=labels[0]).pack(anchor='w', padx=10, pady=(10,0))
    e_name = tk.Entry(win); e_name.pack(fill='x', padx=10)
    entries.append(e_name)

    tk.Label(win, text=labels[1]).pack(anchor='w', padx=10, pady=(8,0))
    e_unit = tk.Entry(win); e_unit.pack(fill='x', padx=10)
    entries.append(e_unit)

    tk.Label(win, text=labels[2]).pack(anchor='w', padx=10, pady=(8,0))
    e_qty = tk.Entry(win); e_qty.pack(fill='x', padx=10)
    entries.append(e_qty)

    tk.Label(win, text=labels[3]).pack(anchor='w', padx=10, pady=(8,0))
    e_min = tk.Entry(win); e_min.pack(fill='x', padx=10)
    entries.append(e_min)

    tk.Label(win, text=labels[4]).pack(anchor='w', padx=10, pady=(8,0))
    # Combobox с именами категорий
    global combobox_category
    combobox_category = ttk.Combobox(win, values=category_names, state="readonly")
    combobox_category.pack(fill='x', padx=10)
    if category_names:
        combobox_category.current(0)

    def save():
        try:
            name = entries[0].get()
            unit = entries[1].get()
            qty = int(entries[2].get())
            min_q = int(entries[3].get())
            cat_name = combobox_category.get()
            # найти id по имени
            cat_id = None
            for cid, cname in categories_list:
                if cname == cat_name:
                    cat_id = cid
                    break
            if cat_id is None:
                raise ValueError("Выберите корректную категорию")

            new_id = add_material(name, unit, qty, min_q, cat_id)
            messagebox.showinfo("Успех", f"Материал добавлен (id={new_id})")
            refresh_table()
            win.destroy()
        except ValueError as ve:
            messagebox.showerror("Ошибка", str(ve))
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    tk.Button(win, text="Сохранить", command=save).pack(pady=12)


def change_quantity_window(operation):
    win = tk.Toplevel(root)
    win.title(operation)
    win.geometry("320x180")

    tk.Label(win, text="ID материала:").pack(anchor='w', padx=10, pady=(10,0))
    e_mid = tk.Entry(win); e_mid.pack(fill='x', padx=10)

    tk.Label(win, text="Количество:").pack(anchor='w', padx=10, pady=(8,0))
    e_amount = tk.Entry(win); e_amount.pack(fill='x', padx=10)

    def save():
        try:
            mid = int(e_mid.get())
            amount = int(e_amount.get())
            if operation == "Приход":
                increase_material(mid, amount)
            else:
                decrease_material(mid, amount)
            messagebox.showinfo("Успех", f"{operation} выполнен")
            refresh_table()
            win.destroy()
        except ValueError as ve:
            messagebox.showerror("Ошибка", str(ve))
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    tk.Button(win, text="OK", command=save).pack(pady=12)


def open_transactions_window():
    win = tk.Toplevel(root)
    win.title("История операций")
    win.geometry("900x400")

    table = ttk.Treeview(
        win,
        columns=("ID","Материал","Тип","Кол-во","Комментарий","Дата"),
        show="headings"
    )

    for col in ("ID","Материал","Тип","Кол-во","Комментарий","Дата"):
        table.heading(col, text=col)
        table.column(col, anchor='w')

    table.pack(fill=tk.BOTH, expand=True)

    for row in load_transactions():
        table.insert("", tk.END, values=row)

def delete_material(selected_id):
    """Удаляет материал и все связанные транзакции"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        # Сначала удаляем транзакции, чтобы не нарушить foreign key
        cur.execute("DELETE FROM transactions WHERE material_id = %s", (selected_id,))
        # Потом удаляем сам материал
        cur.execute("DELETE FROM materials WHERE id = %s", (selected_id,))
        conn.commit()
        messagebox.showinfo("Успех", f"Материал с ID {selected_id} удалён")
    except Exception as e:
        conn.rollback()
        messagebox.showerror("Ошибка", str(e))
    finally:
        cur.close()
        conn.close()
    refresh_table()


def delete_material_window():
    """Вызывается кнопкой удаления"""
    selected = tree.selection()
    if not selected:
        messagebox.showwarning("Внимание", "Выберите материал в таблице")
        return
    item = tree.item(selected[0])
    material_id = item['values'][0]  # ID первой колонки
    material_name = item['values'][1]

    answer = messagebox.askyesno(
        "Подтверждение",
        f"Вы уверены, что хотите удалить материал '{material_name}' (ID {material_id})?"
    )
    if answer:
        delete_material(material_id)

def delete_category(category_id):
    """Удаляет категорию, если нет связанных материалов"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        # Проверка, есть ли материалы в категории
        cur.execute("SELECT COUNT(*) FROM materials WHERE category_id = %s", (category_id,))
        count = cur.fetchone()[0]
        if count > 0:
            messagebox.showwarning("Ошибка", "Нельзя удалить категорию: в ней есть материалы!")
            return

        # Удаляем категорию
        cur.execute("DELETE FROM categories WHERE id = %s", (category_id,))
        conn.commit()
        messagebox.showinfo("Успех", f"Категория с ID {category_id} удалена")
        refresh_categories()
        refresh_table()
    except Exception as e:
        conn.rollback()
        messagebox.showerror("Ошибка", str(e))
    finally:
        cur.close()
        conn.close()


def delete_category_window():
    """Окно выбора категории для удаления"""
    win = tk.Toplevel(root)
    win.title("Удалить категорию")
    win.geometry("300x150")

    tk.Label(win, text="Выберите категорию для удаления:").pack(pady=(10,0))
    combo = ttk.Combobox(win, values=category_names, state="readonly")
    combo.pack(pady=5, padx=10)
    if category_names:
        combo.current(0)

    def delete_selected():
        cat_name = combo.get()
        cat_id = None
        for cid, cname in categories_list:
            if cname == cat_name:
                cat_id = cid
                break
        if cat_id is not None:
            answer = messagebox.askyesno("Подтверждение", f"Удалить категорию '{cat_name}'?")
            if answer:
                delete_category(cat_id)
                win.destroy()

    tk.Button(win, text="Удалить", command=delete_selected).pack(pady=10)

# ---------------------------- ИНИЦИАЛИЗАЦИЯ И ОКНО ----------------------------

# загружаем категории в память
categories_list = []
category_names = []
refresh_categories()

root = tk.Tk()
root.title("Учёт расходных материалов")
root.geometry("900x600")

tree = ttk.Treeview(
    root,
    columns=("ID","Название","Ед.","Количество","Категория"),
    show="headings"
)

for col in ("ID","Название","Ед.","Количество","Категория"):
    tree.heading(col, text=col)
    tree.column(col, anchor='w')

tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

refresh_table()

frame = tk.Frame(root)
frame.pack(pady=6)

tk.Button(frame, text="Добавить категорию", command=add_category_window).grid(row=0, column=0, padx=5)
tk.Button(frame, text="Добавить материал", command=add_material_window).grid(row=0, column=1, padx=5)
tk.Button(frame, text="Приход", command=lambda: change_quantity_window("Приход")).grid(row=0, column=2, padx=5)
tk.Button(frame, text="Расход", command=lambda: change_quantity_window("Расход")).grid(row=0, column=3, padx=5)
tk.Button(frame, text="История операций", command=open_transactions_window).grid(row=0, column=4, padx=5)
tk.Button(frame, text="Обновить", command=refresh_table).grid(row=0, column=5, padx=5)
tk.Button(frame, text="Удалить материал", command=delete_material_window).grid(row=0, column=6, padx=5)
tk.Button(frame, text="Удалить категорию", command=delete_category_window).grid(row=0, column=7, padx=5)

root.mainloop()
