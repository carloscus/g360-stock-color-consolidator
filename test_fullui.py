import flet as ft

def main(page: ft.Page):
    page.bgcolor = "#f0f4f8"
    page.padding = 0
    page.add(
        ft.Column([
            ft.Row([
                ft.Column([
                    ft.Text("Inventory", size=22, weight=ft.FontWeight.BOLD),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Container(expand=True),
                ft.Row([
                    ft.Button("Source 1", icon=ft.icons.Icons.CLOUD_DOWNLOAD_OUTLINED),
                    ft.Button("Source 2", icon=ft.icons.Icons.FILE_DOWNLOAD_OUTLINED),
                ]),
            ]),
            ft.Row([
                ft.Column([
                    ft.Text("Total SKUs", size=12),
                    ft.Text("0", size=22, weight=ft.FontWeight.BOLD),
                ], expand=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Column([
                    ft.Text("Con Stock", size=12),
                    ft.Text("0", size=22, weight=ft.FontWeight.BOLD),
                ], expand=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            ]),
            ft.TextField(hint_text="Buscar..."),
            ft.DataTable(
                columns=[
                    ft.DataColumn(ft.Text("SKU")),
                    ft.DataColumn(ft.Text("Stock")),
                ],
                rows=[],
            ),
        ], spacing=16, expand=True)
    )
    page.update()

if __name__ == "__main__":
    ft.run(main, view=ft.AppView.WEB_BROWSER, port=5190, web_renderer=ft.WebRenderer.CANVAS_KIT)
