import flet as ft
import sqlite3
import json
from datetime import datetime

# --- 1. إعداد قاعدة البيانات ---
def init_db():
    conn = sqlite3.connect("my_store.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT,
            buy_price REAL,
            sell_price REAL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT,
            amount REAL,
            profit REAL,
            details TEXT,
            date TEXT,
            time TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

def main(page: ft.Page):
    page.title = "نظام سامح المتكامل"
    page.rtl = True
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 15
    page.bgcolor = "#F5F7FA"
    
    bold_style = ft.TextStyle(weight=ft.FontWeight.BOLD, size=16)
    all_bills = [{"id": 1, "cart": [], "paid": ""}]
    active_bill_index = 0
    current_selected_item = {"name": "", "price": 0.0}
    starting_cash = 0.0

    def get_val(textfield):
        try:
            return float(textfield.value) if textfield.value else 0.0
        except:
            return 0.0

    # --- إدارة الخزنة ---
    def update_starting_cash(e):
        nonlocal starting_cash
        val = get_val(start_drawer_in)
        if val != 0:
            starting_cash += val
            start_drawer_in.value = ""
            update_safe_logic()
            page.update()

    def update_safe_logic(e=None):
        conn = sqlite3.connect("my_store.db")
        cursor = conn.cursor()
        cursor.execute("SELECT SUM(amount) FROM transactions WHERE type='sale'")
        total_sales = cursor.fetchone()[0] or 0.0
        cursor.execute("SELECT SUM(amount) FROM transactions WHERE type='expense'")
        total_old_expenses = cursor.fetchone()[0] or 0.0
        conn.close()
        current_safe = starting_cash + total_sales - total_old_expenses
        safe_balance_in.value = f"{current_safe:.2f}"
        report_safe_txt.value = f"الخزنة: {current_safe:.2f} ج"
        page.update()

    # --- واجهة الكاشير ---
    start_drawer_in = ft.TextField(label="بداية الدرج (Enter)", expand=True, on_submit=update_starting_cash, keyboard_type=ft.KeyboardType.NUMBER, text_style=bold_style, border_radius=10)
    expenses_in = ft.TextField(label="مصروف جديد (Enter)", expand=True, color="red", on_submit=lambda e: submit_expense(), keyboard_type=ft.KeyboardType.NUMBER, text_style=bold_style, border_radius=10)
    safe_balance_in = ft.TextField(label="رصيد الخزنة الكلي", expand=True, read_only=True, text_style=ft.TextStyle(weight="bold", color="blue", size=20), bgcolor="#E3F2FD", border_radius=10)
    
    def submit_expense():
        val = get_val(expenses_in)
        if val > 0:
            now = datetime.now()
            conn = sqlite3.connect("my_store.db")
            conn.execute("INSERT INTO transactions (type, amount, profit, date, time) VALUES ('expense', ?, 0, ?, ?)", 
                         (val, now.strftime('%Y-%m-%d'), now.strftime('%H:%M:%S')))
            conn.commit(); conn.close()
            expenses_in.value = ""
            update_safe_logic()
            page.update()

    total_req_text = ft.Text("إجمالي المطلوب: 0.00", size=24, weight="bold", color="#2E7D32")
    actual_bill_paid = ft.TextField(label="المدفوع (Enter للحفظ)", width=250, text_style=ft.TextStyle(size=22, weight="bold", color="green"), keyboard_type=ft.KeyboardType.NUMBER, on_submit=lambda _: finalize_invoice(None), border_radius=10)
    
    cart_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("الصنف", weight="bold")), ft.DataColumn(ft.Text("الكمية", weight="bold")), 
            ft.DataColumn(ft.Text("السعر", weight="bold")), ft.DataColumn(ft.Text("حذف", weight="bold"))
        ], rows=[], heading_row_color="#EEEEEE"
    )
    
    bill_tabs_row = ft.Row(spacing=10)
    category_buttons = ft.Row(scroll=ft.ScrollMode.ALWAYS, spacing=10)
    items_grid = ft.GridView(expand=1, runs_count=5, max_extent=140, spacing=10, run_spacing=10) # تم تصغير الحجم هنا

    def update_cart_ui():
        cart_table.rows.clear()
        current_cart = all_bills[active_bill_index]["cart"]
        total = sum(item["price"] for item in current_cart)
        for i, item in enumerate(current_cart):
            cart_table.rows.append(ft.DataRow(cells=[
                ft.DataCell(ft.Text(item["name"], weight="bold")), 
                ft.DataCell(ft.Text(item["qty"], weight="bold")), 
                ft.DataCell(ft.Text(f"{item['price']:.2f}", weight="bold")), 
                ft.DataCell(ft.Text("حذف", color="red", weight="bold"), on_tap=lambda e, idx=i: [current_cart.pop(idx), update_cart_ui()])
            ]))
        total_req_text.value = f"إجمالي المطلوب: {total:.2f}"; page.update()

    def reset_current_bill(e):
        all_bills[active_bill_index]["cart"].clear()
        actual_bill_paid.value = ""
        update_cart_ui()

    def finalize_invoice(e):
        paid_val = get_val(actual_bill_paid)
        current_bill = all_bills[active_bill_index]
        if paid_val > 0 and len(current_bill["cart"]) > 0:
            total_cost = sum(item["cost"] for item in current_bill["cart"])
            actual_profit = paid_val - total_cost
            bill_details = json.dumps(current_bill["cart"])
            now = datetime.now()
            conn = sqlite3.connect("my_store.db")
            conn.execute("INSERT INTO transactions (type, amount, profit, details, date, time) VALUES ('sale', ?, ?, ?, ?, ?)", 
                         (paid_val, actual_profit, bill_details, now.strftime('%Y-%m-%d'), now.strftime('%H:%M:%S')))
            conn.commit(); conn.close()
            if len(all_bills) > 1:
                all_bills.pop(active_bill_index); switch_active_bill(0)
            else:
                current_bill["cart"].clear(); actual_bill_paid.value = ""; update_cart_ui()
            update_safe_logic()

    def switch_active_bill(index):
        nonlocal active_bill_index; active_bill_index = index
        update_cart_ui(); refresh_bill_tabs()

    def refresh_bill_tabs():
        bill_tabs_row.controls.clear()
        for i, b in enumerate(all_bills):
            bill_tabs_row.controls.append(
                ft.Container(
                    content=ft.Text(f"عميل {b['id']}", color="white", weight="bold"),
                    bgcolor="#1976D2" if i==active_bill_index else "#90A4AE",
                    padding=10, border_radius=8,
                    on_click=lambda e, idx=i: switch_active_bill(idx)
                )
            )
        bill_tabs_row.controls.append(ft.OutlinedButton("+ فاتورة جديدة", on_click=lambda _: [all_bills.append({"id":all_bills[-1]["id"]+1, "cart":[], "paid":""}), switch_active_bill(len(all_bills)-1)]))
        page.update()

    # --- نافذة القيمة ---
    amount_input = ft.TextField(label="المبلغ المطلوب", keyboard_type=ft.KeyboardType.NUMBER, text_style=bold_style, border_radius=10, autofocus=True)
    def confirm_amount(e):
        nonlocal current_selected_item
        if not amount_input.value or not current_selected_item["name"]: return
        try:
            mv = float(amount_input.value)
            conn = sqlite3.connect("my_store.db")
            res = conn.execute("SELECT buy_price, sell_price FROM items WHERE name=?", (current_selected_item['name'],)).fetchone()
            buy_p, sell_p = (res[0], res[1]) if res else (0, mv)
            conn.close()
            qty = mv / sell_p if sell_p != 0 else 0
            all_bills[active_bill_index]["cart"].append({"name": current_selected_item['name'], "qty": f"{qty:.3f}", "price": mv, "cost": qty * buy_p})
            update_cart_ui(); amount_input.value = ""; confirm_dlg.open = False; page.update()
        except: pass

    amount_input.on_submit = confirm_amount
    confirm_dlg = ft.AlertDialog(title=ft.Text("أدخل القيمة"), content=amount_input, actions=[ft.FilledButton("إضافة للسلة", on_click=confirm_amount, bgcolor="#2E7D32")])
    page.overlay.append(confirm_dlg)

    def open_amount_dialog(name, price):
        nonlocal current_selected_item
        current_selected_item = {"name": name, "price": price}
        confirm_dlg.title.value = f"قيمة {name}؟"
        confirm_dlg.open = True; page.update()

    def load_items(filter_cat=None):
        items_grid.controls.clear(); conn = sqlite3.connect("my_store.db")
        q = "SELECT name, sell_price FROM items WHERE category=?" if filter_cat and filter_cat != "الكل" else "SELECT name, sell_price FROM items"
        p = (filter_cat,) if filter_cat and filter_cat != "الكل" else ()
        for n, pr in conn.execute(q, p).fetchall():
            items_grid.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Text(n, weight="bold", size=14, color="#0D47A1", text_align="center", max_lines=2), # تصغير الخط قليلاً
                        ft.Text(f"{pr} ج", weight="w500", size=12, color="#546E7A", text_align="center")
                    ], alignment=ft.MainAxisAlignment.CENTER, spacing=2),
                    bgcolor="white", border=ft.Border.all(1, "#BBDEFB"), border_radius=10, padding=5,
                    alignment=ft.Alignment(0, 0), on_click=lambda e, name=n, price=pr: open_amount_dialog(name, price),
                    ink=True, shadow=ft.BoxShadow(blur_radius=2, color="#E0E0E0", offset=ft.Offset(1, 1))
                )
            )
        conn.close(); page.update()

    def load_categories():
        category_buttons.controls.clear(); conn = sqlite3.connect("my_store.db")
        category_buttons.controls.append(ft.FilledButton("الكل", on_click=lambda _: load_items("الكل"), bgcolor="#455A64"))
        for c in conn.execute("SELECT DISTINCT category FROM items").fetchall():
            if c[0]: 
                category_buttons.controls.append(
                    ft.Container(
                        content=ft.Text(c[0], weight="bold", color="white"),
                        bgcolor="#0288D1", padding=ft.Padding(12, 8, 12, 8),
                        border_radius=15, on_click=lambda e, cat=c[0]: load_items(cat)
                    )
                )
        conn.close(); page.update()

    # --- التقارير ---
    report_date_in = ft.TextField(label="تاريخ البحث", value=datetime.now().strftime('%Y-%m-%d'), width=200, text_style=bold_style, border_radius=10)
    report_table = ft.DataTable(columns=[
        ft.DataColumn(ft.Text("التاريخ")), ft.DataColumn(ft.Text("الوقت")), 
        ft.DataColumn(ft.Text("النوع")), ft.DataColumn(ft.Text("المبلغ")), 
        ft.DataColumn(ft.Text("حذف", color="red"))
    ], rows=[], heading_row_color="#F5F5F5")
    
    sales_sum_txt = ft.Text("المبيعات: 0", size=18, weight="bold", color="green")
    profit_sum_txt = ft.Text("الأرباح: 0", size=18, weight="bold", color="blue")
    report_safe_txt = ft.Text("الخزنة: 0", size=18, weight="bold", color="purple")

    def show_bill_details(details_json):
        if not details_json: return
        items = json.loads(details_json)
        d_table = ft.DataTable(columns=[ft.DataColumn(ft.Text("الصنف")), ft.DataColumn(ft.Text("الكمية")), ft.DataColumn(ft.Text("السعر"))], rows=[])
        for it in items:
            d_table.rows.append(ft.DataRow(cells=[ft.DataCell(ft.Text(it['name'])), ft.DataCell(ft.Text(it['qty'])), ft.DataCell(ft.Text(f"{it['price']:.2f}"))]))
        dlg = ft.AlertDialog(title=ft.Text("تفاصيل الفاتورة"), content=ft.Column([d_table], scroll="always", tight=True), 
                             actions=[ft.TextButton("إغلاق", on_click=lambda e: [setattr(dlg, "open", False), page.update()])])
        page.overlay.append(dlg); dlg.open = True; page.update()

    def delete_transaction(trans_id):
        conn = sqlite3.connect("my_store.db")
        conn.execute("DELETE FROM transactions WHERE id=?", (trans_id,))
        conn.commit(); conn.close()
        load_reports(); update_safe_logic()

    def clear_today_sales(e):
        search_date = report_date_in.value
        conn = sqlite3.connect("my_store.db")
        conn.execute("DELETE FROM transactions WHERE date=?", (search_date,))
        conn.commit(); conn.close()
        load_reports(); update_safe_logic()

    def load_reports():
        report_table.rows.clear(); search_date = report_date_in.value
        conn = sqlite3.connect("my_store.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, date, time, type, amount, profit, details FROM transactions WHERE date = ? ORDER BY id DESC", (search_date,))
        ts, tp = 0, 0
        for r in cursor.fetchall():
            if r[3] == 'sale': ts += r[4]; tp += r[5]
            report_table.rows.append(ft.DataRow(cells=[
                ft.DataCell(ft.Text(str(r[1]))), ft.DataCell(ft.Text(str(r[2])[:5])),
                ft.DataCell(ft.Text("بيع" if r[3]=='sale' else "مصروف", color="green" if r[3]=='sale' else "red", weight="bold")), 
                ft.DataCell(ft.Text(f"{r[4]:.2f}", weight="bold"), on_tap=lambda e, d=r[6]: show_bill_details(d)),
                ft.DataCell(ft.Text("حذف سطر", color="red", weight="bold"), on_tap=lambda e, tid=r[0]: delete_transaction(tid))
            ]))
        sales_sum_txt.value = f"المبيعات: {ts:.2f}"; profit_sum_txt.value = f"الأرباح: {tp:.2f}"
        conn.close(); update_safe_logic()

    # --- إدارة المخزن ---
    inventory_table = ft.DataTable(columns=[
        ft.DataColumn(ft.Text("الصنف")), ft.DataColumn(ft.Text("المجموعة")), 
        ft.DataColumn(ft.Text("بيع")), ft.DataColumn(ft.Text("تعديل")), 
        ft.DataColumn(ft.Text("حذف", color="red"))
    ], rows=[])
    
    e_name = ft.TextField(label="اسم الصنف", text_style=bold_style, border_radius=10)
    e_cat = ft.TextField(label="المجموعة", text_style=bold_style, border_radius=10)
    e_buy = ft.TextField(label="شراء", keyboard_type=ft.KeyboardType.NUMBER, text_style=bold_style, border_radius=10)
    e_sell = ft.TextField(label="بيع", keyboard_type=ft.KeyboardType.NUMBER, text_style=bold_style, border_radius=10)
    edit_id_var = None

    def delete_item(item_id):
        conn = sqlite3.connect("my_store.db")
        conn.execute("DELETE FROM items WHERE id=?", (item_id,))
        conn.commit(); conn.close()
        load_inventory(); load_items(); load_categories()

    def clear_all_items(e):
        conn = sqlite3.connect("my_store.db")
        conn.execute("DELETE FROM items")
        conn.commit(); conn.close()
        load_inventory(); load_items(); load_categories(); page.update()

    def update_item_db(e):
        conn = sqlite3.connect("my_store.db")
        conn.execute("UPDATE items SET name=?, category=?, buy_price=?, sell_price=? WHERE id=?", 
                     (e_name.value, e_cat.value, get_val(e_buy), get_val(e_sell), edit_id_var))
        conn.commit(); conn.close(); edit_dlg.open = False
        load_inventory(); load_items(); load_categories(); page.update()

    edit_dlg = ft.AlertDialog(title=ft.Text("تعديل الصنف"), content=ft.Column([e_name, e_cat, e_buy, e_sell], tight=True), actions=[ft.FilledButton("تحديث", on_click=update_item_db)])
    page.overlay.append(edit_dlg)

    def load_inventory():
        inventory_table.rows.clear(); conn = sqlite3.connect("my_store.db")
        for r in conn.execute("SELECT id, name, category, buy_price, sell_price FROM items").fetchall():
            inventory_table.rows.append(ft.DataRow(cells=[
                ft.DataCell(ft.Text(r[1], weight="bold")), ft.DataCell(ft.Text(r[2])), ft.DataCell(ft.Text(str(r[4]), weight="bold")),
                ft.DataCell(ft.Text("تعديل", color="blue", weight="bold"), on_tap=lambda e, row=r: open_edit_dialog(row)),
                ft.DataCell(ft.Text("حذف صنف", color="red", weight="bold"), on_tap=lambda e, iid=r[0]: delete_item(iid))
            ]))
        conn.close(); page.update()

    def open_edit_dialog(row):
        nonlocal edit_id_var; edit_id_var = row[0]
        e_name.value=row[1]; e_cat.value=row[2]; e_buy.value=str(row[3]); e_sell.value=str(row[4])
        edit_dlg.open=True; page.update()

    # --- بناء الواجهات ---
    cashier_view = ft.Column([
        ft.Row([start_drawer_in, expenses_in, safe_balance_in]), 
        bill_tabs_row, 
        ft.Row([
            ft.Column([category_buttons, items_grid], expand=3), 
            ft.Column([
                ft.Container(content=ft.Row([ft.Text("الفاتورة الحالية", weight="bold", size=18), ft.FilledButton("تصفير الفاتورة", bgcolor="#C62828", on_click=reset_current_bill)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), padding=5),
                ft.Container(content=ft.Column([cart_table], scroll="always"), expand=1, border=ft.Border.all(1, "#CFD8DC"), border_radius=10, bgcolor="white"), 
                total_req_text, 
                ft.Row([actual_bill_paid, ft.FilledButton("حفظ الفاتورة", bgcolor="#2E7D32", height=50, on_click=finalize_invoice)])
            ], expand=2)
        ], expand=True)
    ], expand=True)

    report_view = ft.Column([
        ft.Row([report_date_in, ft.FilledButton("بحث", on_click=lambda _: load_reports(), bgcolor="#0288D1"), ft.FilledButton("تصفير مبيعات اليوم", bgcolor="#C62828", on_click=clear_today_sales)]), 
        ft.Row([sales_sum_txt, profit_sum_txt, report_safe_txt], spacing=40), 
        ft.Divider(), 
        ft.Container(content=ft.Column([report_table], scroll="always"), expand=True, bgcolor="white", border_radius=10, padding=10)
    ], visible=False, expand=True)

    add_view = ft.Column([
        ft.Row([ft.Text("إدارة المخزن", weight="bold", size=20), ft.FilledButton("مسح كل المخزن", bgcolor="#C62828", on_click=clear_all_items)]),
        ft.Row([e_name, e_cat, e_buy, e_sell]), 
        ft.FilledButton("تسجيل صنف جديد", on_click=lambda _: [sqlite3.connect("my_store.db").execute("INSERT INTO items (name, category, buy_price, sell_price) VALUES (?,?,?,?)", (e_name.value, e_cat.value, get_val(e_buy), get_val(e_sell))).connection.commit(), load_inventory(), load_items(), load_categories()], bgcolor="#1565C0"), 
        ft.Divider(), 
        ft.Container(content=ft.Column([inventory_table], scroll="always"), expand=True, bgcolor="white", border_radius=10, padding=10)
    ], visible=False, expand=True)

    def switch(e):
        cashier_view.visible=(e.control.data=="c"); report_view.visible=(e.control.data=="r"); add_view.visible=(e.control.data=="a")
        if report_view.visible: load_reports()
        if add_view.visible: load_inventory()
        page.update()

    page.add(
        ft.Container(
            content=ft.Row([
                ft.TextButton("شاشة البيع", data="c", on_click=switch, style=ft.ButtonStyle(color="#1565C0")),
                ft.TextButton("تقارير الأرباح", data="r", on_click=switch, style=ft.ButtonStyle(color="#EF6C00")),
                ft.TextButton("إدارة المخزن", data="a", on_click=switch, style=ft.ButtonStyle(color="#455A64")),
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=30),
            bgcolor="white", padding=10, border_radius=15, shadow=ft.BoxShadow(blur_radius=5, color="#CCCCCC")
        ),
        ft.Divider(height=10, color="transparent"),
        cashier_view, report_view, add_view
    )
    
    refresh_bill_tabs(); load_categories(); load_items(); update_safe_logic()

ft.run(main)
