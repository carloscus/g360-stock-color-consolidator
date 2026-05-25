import flet as ft

def main(page: ft.Page):
    page.padding = 24
    page.bgcolor = "#f0f4f8"
    c = ft.Container(
        ft.Text("Container SIMPLE sin expand", size=18, color="#1e293b"),
        bgcolor="#ffffff",
        border_radius=10,
        padding=16,
    )
    page.add(c)
    page.update()

if __name__ == "__main__":
    ft.run(main, view=ft.AppView.WEB_BROWSER, port=5189, web_renderer=ft.WebRenderer.HTML)
