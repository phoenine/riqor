# Playwright testcase patterns

## Ordinary testcase

Use the runtime-managed page so failures retain evidence:

```python
import pytest
from playwright.sync_api import expect


@pytest.mark.rigor_source(
    automation_id="AUTO-014",
    requirements=["REQ-008"],
    test_points=["TP-006"],
    test_cases=["TC-014"],
)
def test_checkout_summary_matches_cart(web_page, webtest_config):
    """TC-014 / TP-006 / REQ-008: checkout displays the selected cart total."""
    web_page.goto(f"{webtest_config.base_url}checkout")
    expect(web_page.get_by_test_id("order-total")).to_have_text("$42.00")
```

Prefer role, label, placeholder, text, or test-id locators. Put selectors and
interactions in a project Page/Component Object when they are reused. Use CSS or
XPath only when the product exposes no stable semantic locator.

## Project authentication fixture

Authentication remains project-owned. Observe a manually created page before an
operation that can fail:

```python
import os
import pytest


@pytest.fixture
def authenticated_page(webtest_config, web_observer, browser):
    context = browser.new_context()
    page = web_observer.observe(context.new_page())
    page.goto(f"{webtest_config.base_url}login")
    page.get_by_label("Email").fill(os.environ["WEBTEST_USERNAME"])
    page.get_by_label("Password").fill(os.environ["WEBTEST_PASSWORD"])
    page.get_by_role("button", name="Sign in").click()
    page.wait_for_url(f"{webtest_config.base_url}home")
    yield page
    context.close()
```

For reusable `storage_state`, create it in a session fixture and create a fresh
browser context per testcase. Never persist authenticated state in source control.

## Synchronization and assertions

- Wait for the DOM, URL, response, download, or application state that proves the
  action completed. Do not use a fixed timeout as a substitute.
- Assert the user-visible or contract-visible result. Element existence is
  insufficient when the requirement concerns value, state, navigation,
  persistence, or a side effect.
- For a relevant network contract, combine the action with `expect_response` and
  assert both the response and resulting UI state.
- Negative tests must fail when the rejected action unexpectedly succeeds.

Use `pytest.skip` only for an explicitly declared, independently verified
environmental precondition. Never catch broad exceptions to accept a weaker
fallback state.
