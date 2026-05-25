import flet as ft

def main(page: ft.Page):
    page.padding = 24
    page.bgcolor = "#f0f4f8"
    page.add(
        ft.Column([
            ft.Container(
                ft.Text("Header con Container", size=18, color="#1e293b"),
                bgcolor="#ffffff",
                border_radius=10,
                padding=16,
            ),
            ft.Row([
                ft.Container(ft.Text("Card 1"), bgcolor="#ffffff", border_radius=10, padding=16, expand=True),
                ft.Container(ft.Text("Card 2"), bgcolor="#ffffff", border_radius=10, padding=16, expand=True),
            ], spacing=12),
        ], spacing=16, expand=True)
    )
    page.update()

if __name__ == "__main__":
    ft.run(main, view=ft.AppView.WEB_BROWSER, port=5185, web_renderer=ft.WebRenderer.CANVAS_KIT)
