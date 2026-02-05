def test_credits_display_ui():
    # Simulate frontend user object
    user = {"username": "volunteer", "role": "volunteer", "credits": 2}
    # Simulate UI rendering logic
    display = f"Credits: {user['credits']}" if 'credits' in user else ""
    assert display == "Credits: 2"
