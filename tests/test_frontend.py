from uuid import uuid4

from playwright.sync_api import Page, expect


def test_activity_card_renders_participants_without_bullets(page: Page):
    # Arrange
    response = page.request.get("/activities")
    assert response.ok
    activity_name, activity = next(iter(response.json().items()))
    participant_email = activity["participants"][0]

    # Act
    page.goto("/")
    card = page.locator(".activity-card").filter(
        has=page.get_by_role("heading", name=activity_name)
    )

    # Assert
    expect(card.get_by_text(participant_email, exact=True)).to_be_visible()
    expect(card.locator(".participant-list")).to_have_css("list-style-type", "none")


def test_signup_updates_card_without_page_reload(page: Page):
    # Arrange
    response = page.request.get("/activities")
    assert response.ok
    activity_name, activity = next(iter(response.json().items()))
    original_participant_count = len(activity["participants"])
    email = f"test-{uuid4().hex}@example.com"
    document_token = str(uuid4())

    # Act
    page.goto("/")
    page.evaluate("token => { window.__testDocumentToken = token; }", document_token)
    try:
        page.locator("#email").fill(email)
        page.locator("#activity").select_option(activity_name)
        page.get_by_role("button", name="Sign Up").click()

        card = page.locator(".activity-card").filter(
            has=page.get_by_role("heading", name=activity_name)
        )
        expect(card.get_by_text(email, exact=True)).to_be_visible()
        expect(card.get_by_role("heading", name=f"Participants ({original_participant_count + 1})")).to_be_visible()
        expect(page.locator("#message")).to_contain_text(f"Signed up {email} for {activity_name}")
        assert page.evaluate("window.__testDocumentToken") == document_token
    finally:
        page.request.delete(
            f"/activities/{activity_name}/participants",
            params={"email": email},
        )


def test_remove_button_unregisters_participant_and_updates_card(page: Page):
    # Arrange
    response = page.request.get("/activities")
    assert response.ok
    activity_name, activity = next(iter(response.json().items()))
    original_participant_count = len(activity["participants"])
    email = f"test-{uuid4().hex}@example.com"
    registration = page.request.post(
        f"/activities/{activity_name}/signup",
        params={"email": email},
    )
    assert registration.ok
    document_token = str(uuid4())

    try:
        page.goto("/")
        page.evaluate("token => { window.__testDocumentToken = token; }", document_token)
        card = page.locator(".activity-card").filter(
            has=page.get_by_role("heading", name=activity_name)
        )

        # Act
        card.get_by_role("button", name=f"Unregister {email}").click()

        # Assert
        expect(card.get_by_text(email, exact=True)).to_have_count(0)
        expect(card.get_by_role("heading", name=f"Participants ({original_participant_count})")).to_be_visible()
        expect(page.locator("#message")).to_contain_text(f"Unregistered {email} from {activity_name}")
        assert page.evaluate("window.__testDocumentToken") == document_token
    finally:
        page.request.delete(
            f"/activities/{activity_name}/participants",
            params={"email": email},
        )
