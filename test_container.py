import flet as ft

def main(page: ft.Page):
    with open("debug2.log", "w") as f:
        f.write("start\n")
        try:
            container = ft.Container(
                content=ft.Column([
                    ft.Text("Hola G360!", size=30, color="green"),
                    ft.ElevatedButton("Test Button", on_click=lambda e: f.write("clicked\n")),
                ]),
                bgcolor="#f0f4f8",
                expand=True,
            )
            page.add(container)
            page.update()
            f.write("done\n")
        except Exception as e:
            f.write(f"error: {e}\n")

if __name__ == "__main__":
    ft.run(main, view=ft.AppView.WEB_BROWSER, port=5183, web_renderer=ft.WebRenderer.CANVAS_KIT)
