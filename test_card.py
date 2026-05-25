import flet as ft

def main(page: ft.Page):
    page.padding = 24
    page.bgcolor = "#f0f4f8"
    page.add(
        ft.Column([
            ft.Card(
                ft.Text("Card content", size=18),
            ),
            ft.Card(
                ft.Row([
                    ft.Text("Left"),
                    ft.Container(expand=True),
                    ft.Text("Right"),
                ])
            ),
        ], spacing=16, expand=True)
    )
    page.update()

if __name__ == "__main__":
    ft.run(main, view=ft.AppView.WEB_BROWSER, port=5187, web_renderer=ft.WebRenderer.CANVAS_KIT)
