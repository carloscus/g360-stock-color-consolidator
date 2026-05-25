import flet as ft

def main(page: ft.Page):
    page.padding = 24
    page.bgcolor = "#f0f4f8"
    page.add(
        ft.Column([
            ft.Text("SIN Container - funciona?", size=18),
            ft.Row([
                ft.Column([ft.Text("A"), ft.Text("B")], expand=True),
                ft.Column([ft.Text("C"), ft.Text("D")], expand=True),
            ], spacing=12),
        ], spacing=16)
    )
    page.update()

if __name__ == "__main__":
    ft.run(main, view=ft.AppView.WEB_BROWSER, port=5186, web_renderer=ft.WebRenderer.CANVAS_KIT)
