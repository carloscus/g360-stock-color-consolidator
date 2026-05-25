import flet as ft

def main(page: ft.Page):
    page.add(ft.Text("Hola G360!", size=30, color="green"))

if __name__ == "__main__":
    ft.run(main, view=ft.AppView.WEB_BROWSER, port=5181, web_renderer=ft.WebRenderer.CANVAS_KIT)
