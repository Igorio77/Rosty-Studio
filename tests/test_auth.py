from rostify.services.auth import hash_password, verify_password


def test_hash_password_never_returns_plaintext():
    stored = hash_password("hunter2")
    assert "hunter2" not in stored
    assert "$" in stored


def test_hash_password_empty_means_no_password():
    assert hash_password("") == ""


def test_same_password_hashes_differently_each_time():
    a = hash_password("hunter2")
    b = hash_password("hunter2")
    assert a != b  # random salt


def test_verify_password_round_trip():
    stored = hash_password("hunter2")
    assert verify_password("hunter2", stored) is True
    assert verify_password("wrong", stored) is False


def test_verify_password_rejects_empty_stored_hash():
    assert verify_password("anything", "") is False
