import flet as ft
from datetime import datetime, timedelta
import json

# --- GLOBAL STATE & DATABASE ---
STATE = {"user_name": "", "selected_date": datetime.now()}
DEFAULT_DB = {
    "settings": {"rate": 1500, "jazzcash": "0300-1234567", "advance": 500},
    "master_data": {},
    "pending_requests": [],
    "approved_bookings": []
}
DB = DEFAULT_DB.copy()

def main(page: ft.Page):
    page.title = "Indoor Cricket Club"
    page.window_width = 390
    page.window_height = 800
    page.theme_mode = "light"
    page.padding = 15

    # --- DATA PERSISTENCE (Mobile Friendly) ---
    def load_db():
        global DB
        raw = page.client_storage.get("club_db")
        if raw:
            DB = json.loads(raw)
        else:
            DB = DEFAULT_DB.copy()

    def save_db():
        page.client_storage.set("club_db", json.dumps(DB))

    load_db()

    def logout(e):
        STATE["user_name"] = ""
        start_screen()

    # --- ADMIN LOGIC ---
    def handle_admin_action(req, status):
        d_key, s_key = req['date'], req['slot']
        if d_key not in DB["master_data"]:
            DB["master_data"][d_key] = {}
        
        DB["master_data"][d_key][s_key]["status"] = status
        
        if status == "Booked":
            DB["approved_bookings"].append(req)
        
        # Remove from pending requests
        DB["pending_requests"] = [r for r in DB["pending_requests"] if not (r['date'] == d_key and r['slot'] == s_key)]
        
        save_db()
        show_admin_dashboard()

    # --- 1. ADMIN DASHBOARD ---
    def show_admin_dashboard():
        page.clean()
        pending_count = len(DB["pending_requests"])
        
        notif = ft.Container(
            content=ft.Text(f"🔔 {pending_count} New Bookings" if pending_count > 0 else "✅ All Clear", color="white", weight="bold"),
            bgcolor="orange" if pending_count > 0 else "green",
            padding=12, border_radius=10, alignment=ft.alignment.center
        )

        r_field = ft.TextField(label="Hourly Rate", value=str(DB["settings"]["rate"]), width=110)
        n_field = ft.TextField(label="JazzCash/EasyPaisa", value=DB["settings"]["jazzcash"], width=200)

        # Pending Requests List
        pending_list = ft.Column(spacing=10, scroll="auto")
        for r in DB["pending_requests"]:
            pending_list.controls.append(
                ft.Card(content=ft.Container(padding=15, content=ft.Column([
                    ft.Text(f"User: {r['user']}", weight="bold", size=18, color="blue900"),
                    ft.Text(f"Slot: {r['date']} | {r['slot']}"),
                    ft.Row([
                        ft.ElevatedButton("Approve ✅", bgcolor="green", color="white", on_click=lambda e, req=r: handle_admin_action(req, "Booked")),
                        ft.TextButton("Reject ❌", on_click=lambda e, req=r: handle_admin_action(req, "Available"), style=ft.ButtonStyle(color="red"))
                    ], alignment="end")
                ])))
            )

        # History List
        history_list = ft.Column([
            ft.ListTile(leading=ft.Icon(ft.icons.PERSON), title=ft.Text(f"{h['user']} - {h['slot']}"), subtitle=ft.Text(f"Date: {h['date']}"))
            for h in DB["approved_bookings"]
        ], scroll="auto")

        page.add(
            ft.Row([ft.Text("Admin Control", size=22, weight="bold"), ft.Icon(ft.icons.ADMIN_PANEL_SETTINGS)], alignment="spaceBetween"),
            notif,
            ft.Row([r_field, n_field], alignment="center"),
            ft.ElevatedButton("Save App Settings", icon=ft.icons.SAVE, on_click=lambda _: (DB["settings"].update({"rate": int(r_field.value), "jazzcash": n_field.value}), save_db())),
            ft.Divider(),
            ft.Tabs(expand=True, tabs=[
                ft.Tab(text="Requests", content=ft.Container(content=pending_list, padding=10)),
                ft.Tab(text="History", content=ft.Container(content=history_list, padding=10))
            ]),
            ft.ElevatedButton("Logout From Admin", icon=ft.icons.LOGOUT, on_click=logout, width=400, height=50, bgcolor="red50", color="red900")
        )
        page.update()

    # --- 2. USER SCREEN ---
    def show_user_screen():
        page.clean()
        date_str = STATE["selected_date"].strftime("%Y-%m-%d")
        
        if date_str not in DB["master_data"]:
            DB["master_data"][date_str] = {f"{i:02d}:00": {"status": "Available"} for i in range(24)}

        # Date Picker Fix
        def on_date_change(e):
            STATE["selected_date"] = e.control.value
            show_user_screen()

        picker = ft.DatePicker(on_change=on_date_change, first_date=datetime.now())
        page.overlay.append(picker)

        # Slots Grid
        grid = ft.GridView(expand=True, runs_count=3, child_aspect_ratio=1.6, spacing=10)
        for t in sorted(DB["master_data"][date_str].keys()):
            status = DB["master_data"][date_str][t]["status"]
            bg, txt, lbl = ("blue50", "blue", t)
            if status == "Pending": bg, txt, lbl = ("orange100", "orange", "Pending")
            elif status == "Booked": bg, txt, lbl = ("grey200", "grey600", "Booked")

            grid.controls.append(ft.Container(
                content=ft.Text(lbl, size=10, weight="bold", color=txt),
                alignment=ft.alignment.center, bgcolor=bg, border_radius=10,
                on_click=lambda e, s=t: open_payment_ui(s) if DB["master_data"][date_str][s]["status"]=="Available" else None
            ))

        page.add(
            ft.Row([ft.Text(f"Welcome, {STATE['user_name']}", weight="bold", size=18), ft.IconButton(ft.icons.LOGOUT, on_click=logout)], alignment="spaceBetween"),
            ft.ElevatedButton(f"Change Date: {date_str}", icon=ft.icons.CALENDAR_MONTH, on_click=lambda _: picker.pick_date(), width=400),
            ft.Text(f"Ground Rate: Rs. {DB['settings']['rate']}/Hour", color="green", weight="bold"),
            ft.Divider(),
            grid
        )
        page.update()

    # --- 3. PAYMENT UI ---
    def open_payment_ui(slot):
        def on_confirm(e):
            d_str = STATE["selected_date"].strftime("%Y-%m-%d")
            DB["master_data"][d_str][slot]["status"] = "Pending"
            DB["pending_requests"].append({"user": STATE["user_name"], "date": d_str, "slot": slot})
            save_db()
            page.dialog.open = False
            page.update()
            show_user_screen()

        page.dialog = ft.AlertDialog(
            title=ft.Text("Booking Confirmation"),
            content=ft.Container(
                height=240,
                content=ft.Column([
                    ft.Text(f"Slot: {slot}", weight="bold"),
                    ft.Container(
                        padding=10, bgcolor="red50", border_radius=8,
                        content=ft.Text(f"Advance Required: Rs. {DB['settings']['advance']}", color="red", weight="bold")
                    ),
                    ft.Text("Transfer to JazzCash/EasyPaisa:", size=12),
                    ft.Container(
                        padding=15, bgcolor="blue50", border_radius=10, alignment=ft.alignment.center,
                        content=ft.Text(DB["settings"]["jazzcash"], size=24, weight="bold", color="blue900")
                    ),
                    ft.Text("⚠️ Send screenshot on WhatsApp", size=11, italic=True)
                ], spacing=12)
            ),
            actions=[
                ft.ElevatedButton("Sent ✅", on_click=on_confirm, bgcolor="green", color="white"),
                ft.TextButton("Cancel", on_click=lambda _: (setattr(page.dialog, "open", False), page.update()), style=ft.ButtonStyle(color="red"))
            ],
            actions_alignment="end"
        )
        page.dialog.open = True
        page.update()

    # --- 4. START SCREEN (LOGIN) ---
    def start_screen():
        page.clean()
        page.overlay.clear()
        name_in = ft.TextField(label="Full Name", width=350, prefix_icon=ft.icons.PERSON)
        
        def do_login(e):
            if name_in.value.strip():
                STATE["user_name"] = name_in.value
                if name_in.value.lower() == "admin":
                    show_admin_dashboard()
                else:
                    show_user_screen()
            else:
                name_in.error_text = "Please enter your name first!"
                page.update()

        page.add(
            ft.Container(height=80),
            ft.Column([
                ft.Icon(ft.icons.SPORTS_CRICKET, size=100, color="blue"),
                ft.Text("Indoor Cricket Club", size=28, weight="bold", color="blue900"),
                ft.Container(height=20),
                name_in,
                ft.ElevatedButton("Login to App", on_click=do_login, width=350, height=50)
            ], horizontal_alignment="center")
        )
        page.update()

    start_screen()

# Mobile optimized
ft.app(target=main)