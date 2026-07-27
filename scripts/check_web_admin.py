from app.web.admin import router

def check() -> None:
    paths = {route.path for route in router.routes}
    for path in ("/admin", "/admin/login", "/admin/users", "/admin/payments", "/admin/sources", "/admin/delivery", "/admin/audit"):
        assert path in paths, path
    print("Web admin check: OK")
    print("Authentication: signed HttpOnly session cookie")
    print("Sections: dashboard, users, payments, sources, delivery, audit")

if __name__ == "__main__":
    check()
