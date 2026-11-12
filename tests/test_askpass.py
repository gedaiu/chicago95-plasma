import subprocess
import sys

import pytest
from conftest import REPO, load_script
from PySide6.QtWidgets import QDialog, QLineEdit


@pytest.fixture(scope="session")
def askpass():
    return load_script("chicago95-askpass")


def test_prompt_shows_what_sudo_asks_and_hides_what_is_typed(askpass, qt_app):
    prompt = askpass.PasswordPrompt("[sudo] password for me: ")

    assert (prompt.question.text(), prompt.password_edit.echoMode()) == ("[sudo] password for me: ", QLineEdit.Password)


def test_ok_accepts_the_prompt_with_the_typed_password(askpass, qt_app):
    prompt = askpass.PasswordPrompt("Password:")
    prompt.password_edit.setText("hunter2")
    prompt.ok_button.click()

    assert (prompt.result(), prompt.password()) == (QDialog.Accepted, "hunter2")


def test_cancel_rejects_the_prompt(askpass, qt_app):
    prompt = askpass.PasswordPrompt("Password:")
    prompt.password_edit.setText("hunter2")
    prompt.cancel_button.click()

    assert prompt.result() == QDialog.Rejected


def test_main_prints_the_password_and_succeeds_when_accepted(askpass, qt_app, capsys):
    def type_and_accept(prompt):
        prompt.password_edit.setText("hunter2")
        prompt.ok_button.click()

    exit_code = askpass.main(["chicago95-askpass", "Password:"], execute=type_and_accept)

    assert (exit_code, capsys.readouterr().out) == (0, "hunter2\n")


def test_main_prints_nothing_and_fails_when_cancelled(askpass, qt_app, capsys):
    exit_code = askpass.main(["chicago95-askpass"], execute=lambda prompt: prompt.cancel_button.click())

    assert (exit_code, capsys.readouterr().out) == (1, "")


def test_main_asks_a_plain_password_question_when_sudo_gives_none(askpass, qt_app):
    questions = []
    askpass.main(
        ["chicago95-askpass"],
        execute=lambda prompt: questions.append(prompt.question.text()) or prompt.cancel_button.click(),
    )

    assert questions == ["Password:"]


def test_screenshot_option_saves_a_picture_of_the_prompt(tmp_path):
    picture = tmp_path / "askpass.png"
    result = subprocess.run(
        [sys.executable, str(REPO / "bin/chicago95-askpass"), "--screenshot", str(picture)],
        capture_output=True,
        text=True,
        timeout=60,
        env={
            "PATH": "/usr/bin:/bin",
            "SETUP_OS_RELEASE": "/dev/null",
            "HOME": str(tmp_path),
            "QT_QPA_PLATFORM": "offscreen",
        },
        check=False,
    )

    assert (result.returncode, picture.stat().st_size > 0) == (0, True)
