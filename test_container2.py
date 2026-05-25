import flet as ft

def main(page: ft.Page):
    page.padding = 24
    page.bgcolor = "#f0f4f8"
    c = ft.Container(
        ft.Text("Test", size=18),
        padding=16,
    )
    c.bgcolor = "#ffffff"
    c.border_radius = 10
    page.add(c)
    page.update()

if __name__ == "__main__":
    ft.run(main, view=ft.AppView.WEB_BROWSER, port=5191, web_renderer=ft.WebRenderer.CANVAS_KIT)
