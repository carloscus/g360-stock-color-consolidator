import flet as ft

def main(page: ft.Page):
    page.title = "G360 - Test Build"
    page.padding = 0
    page.window.width = 1280
    page.window.height = 820
    page.bgcolor = "#f0f4f8"

    # Simulate what _build does minimally
    container = ft.Container(
        content=ft.Column(
            [
                ft.Container(
                    content=ft.Row([
                        ft.Text("Stock Color Consolidator", size=22, weight=ft.FontWeight.BOLD),
                        ft.Container(expand=True),
                        ft.ElevatedButton("Cargar Source 1"),
                    ]),
                    padding=ft.Padding.symmetric(vertical=16),
                ),
                ft.Container(
                    content=ft.Text("KPI cards go here", size=14, color="gray"),
                    bgcolor="white",
                    border_radius=14,
                    padding=ft.Padding.all(16),
                ),
            ],
            spacing=16,
        ),
        expand=True,
        padding=ft.Padding.only(left=24, right=24, top=0, bottom=24),
    )

    page.clean()
    page.add(container)
    page.update()

if __name__ == "__main__":
    ft.run(main, view=ft.AppView.WEB_BROWSER, port=5182, web_renderer=ft.WebRenderer.CANVAS_KIT)
