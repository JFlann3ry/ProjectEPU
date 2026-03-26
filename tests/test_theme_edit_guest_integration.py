import re

from fastapi.testclient import TestClient

from app.models.event import Event, Theme
from app.models.user import User
from app.services.auth import create_session


def _extract_csrf(html: str) -> str:
    m = re.search(r'name="csrf_token"\s+value="([^"]*)"', html)
    assert m, "csrf_token input not found"
    return m.group(1)


def test_edit_theme_then_guest_page_reflects_saved_style(db_session, client: TestClient):
    # Ensure a user exists and authenticate the client.
    user = db_session.query(User).filter(User.Email == "theme_flow_user@example.test").first()
    if not user:
        user = User(
            FirstName="Theme",
            LastName="Flow",
            Email="theme_flow_user@example.test",
            HashedPassword="x",
            IsActive=True,
        )
        db_session.add(user)
        db_session.flush()

    sess = create_session(db_session, user_id=int(getattr(user, "UserID")))
    client.cookies.set("session_id", str(sess.SessionID))

    # Create an event owned by this user and a preset theme with a solid button style.
    event = Event(
        EventTypeID=None,
        UserID=int(getattr(user, "UserID")),
        Name="Theme Integration Event",
        Code="THMINT01",
        Password="secret",
        Published=True,
        TermsChecked=True,
    )
    db_session.add(event)

    theme = Theme(
        Name="Integration Solid Theme",
        Description="Integration test theme",
        IsActive=True,
        ButtonColour1="#101010",
        ButtonColour2="#202020",
        ButtonStyle="solid",
        BackgroundColour="#f7f7f7",
        FontFamily="Lato, sans-serif",
        TextColour="#111111",
        AccentColour="#333333",
        InputBackgroundColour="#121212",
        DropzoneBackgroundColour="#141414",
    )
    db_session.add(theme)
    db_session.flush()

    # Load edit page to obtain csrf token and cookies.
    edit_page = client.get(f"/e/{event.Code}/edit")
    assert edit_page.status_code == 200
    csrf = _extract_csrf(edit_page.text)

    # Save the selected preset theme.
    save_resp = client.post(
        f"/e/{event.Code}/edit",
        data={
            "name": "Theme Integration Event",
            "theme_id": str(theme.ThemeID),
            "csrf_token": csrf,
        },
        follow_redirects=False,
    )
    assert save_resp.status_code in (302, 303)

    # Guest page should render using the saved style and computed gradient var.
    guest_page = client.get(f"/guest/upload/{event.Code}")
    assert guest_page.status_code == 200
    html = guest_page.text

    assert 'id="guest-theme" class="theme-root section-bg-only is-solid"' in html
    assert "--btn-gradient: linear-gradient(90deg, #101010 0%, #202020 100%);" in html


def test_edit_page_rerenders_gradient_when_overriding_solid_theme(db_session, client: TestClient):
    """Regression: server-rendered edit page must reflect the saved button style,
    not revert to the preset theme's default ButtonStyle on reload."""
    user = db_session.query(User).filter(User.Email == "theme_flow_revert@example.test").first()
    if not user:
        user = User(
            FirstName="Theme",
            LastName="Revert",
            Email="theme_flow_revert@example.test",
            HashedPassword="x",
            IsActive=True,
        )
        db_session.add(user)
        db_session.flush()

    sess = create_session(db_session, user_id=int(getattr(user, "UserID")))
    client.cookies.set("session_id", str(sess.SessionID))

    event = Event(
        EventTypeID=None,
        UserID=int(getattr(user, "UserID")),
        Name="Theme Revert Regression",
        Code="THMREV01",
        Password="secret",
        Published=True,
        TermsChecked=True,
    )
    db_session.add(event)

    # Preset theme that uses solid buttons.
    theme = Theme(
        Name="Solid Preset Theme",
        IsActive=True,
        ButtonColour1="#aabbcc",
        ButtonColour2="#ccbbaa",
        ButtonStyle="solid",
        BackgroundColour="#ffffff",
        TextColour="#000000",
    )
    db_session.add(theme)
    db_session.flush()

    edit_page = client.get(f"/e/{event.Code}/edit")
    assert edit_page.status_code == 200
    csrf = _extract_csrf(edit_page.text)

    # User saves with the solid preset theme selected but explicitly sets button_style=gradient.
    save_resp = client.post(
        f"/e/{event.Code}/edit",
        data={
            "name": "Theme Revert Regression",
            "theme_id": str(theme.ThemeID),
            "button_style": "gradient",
            "button_gradient_style": "linear",
            "button_gradient_direction": "90deg",
            "csrf_token": csrf,
        },
        follow_redirects=False,
    )
    assert save_resp.status_code in (302, 303)

    # Reload edit page — server must render button_style="gradient", not "solid".
    reload_resp = client.get(f"/e/{event.Code}/edit")
    assert reload_resp.status_code == 200
    html = reload_resp.text

    # The hidden input must carry the saved gradient value, not the theme default.
    assert 'name="button_style" value="gradient"' in html
    assert 'name="button_style" value="solid"' not in html

    # The gradient radio must be marked checked by the server.
    assert 'id="ButtonStyleGradient"' in html
    assert 'id="ButtonStyleSolid" value="solid" checked' not in html


def test_edit_custom_gradient_then_guest_page_reflects_saved_gradient(
    db_session, client: TestClient
):
    user = db_session.query(User).filter(User.Email == "theme_flow_grad@example.test").first()
    if not user:
        user = User(
            FirstName="Theme",
            LastName="Gradient",
            Email="theme_flow_grad@example.test",
            HashedPassword="x",
            IsActive=True,
        )
        db_session.add(user)
        db_session.flush()

    sess = create_session(db_session, user_id=int(getattr(user, "UserID")))
    client.cookies.set("session_id", str(sess.SessionID))

    event = Event(
        EventTypeID=None,
        UserID=int(getattr(user, "UserID")),
        Name="Theme Integration Gradient Event",
        Code="THMINT02",
        Password="secret",
        Published=True,
        TermsChecked=True,
    )
    db_session.add(event)
    db_session.flush()

    edit_page = client.get(f"/e/{event.Code}/edit")
    assert edit_page.status_code == 200
    csrf = _extract_csrf(edit_page.text)

    save_resp = client.post(
        f"/e/{event.Code}/edit",
        data={
            "name": "Theme Integration Gradient Event",
            "theme_id": "",
            "button_style": "gradient",
            "button_gradient_style": "radial",
            "button_gradient_direction": "45deg",
            "primary_color": "#aa1122",
            "secondary_color": "#22aa11",
            "csrf_token": csrf,
        },
        follow_redirects=False,
    )
    assert save_resp.status_code in (302, 303)

    guest_page = client.get(f"/guest/upload/{event.Code}")
    assert guest_page.status_code == 200
    html = guest_page.text

    assert 'id="guest-theme" class="theme-root section-bg-only is-gradient"' in html
    assert "--btn-gradient: radial-gradient(circle at center, #aa1122 0%, #22aa11 100%);" in html
