import flet as ft

def main(page: ft.Page):
    page.bgcolor = "#f0f4f8"
    page.add(
        ft.Column([
            ft.Text("Hola G360!", size=30, color="green"),
            ft.Button("Test Button"),
        ])
    )
    page.update()

if __name__ == "__main__":
    ft.run(main, view=ft.AppView.WEB_BROWSER, port=5184, web_renderer=ft.WebRenderer.CANVAS_KIT)
