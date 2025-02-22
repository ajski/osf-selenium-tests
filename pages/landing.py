from selenium.webdriver.common.by import By

import settings
from base.locators import (
    ComponentLocator,
    GroupLocator,
    Locator,
)
from components.generic import SignUpForm
from components.navbars import EmberNavbar
from pages.base import OSFBasePage


class LandingPage(OSFBasePage):
    identity = Locator(By.CSS_SELECTOR, '._heroHeader_1qc5dv', settings.LONG_TIMEOUT)

    get_started_button = Locator(By.CSS_SELECTOR, '[data-test-get-started-button]')
    search_input = Locator(By.CSS_SELECTOR, '[data-test-search-input]')
    learn_more_button = Locator(
        By.CSS_SELECTOR, '[data-analytics-name="Learn more button"]'
    )
    testimonial_1_slide = Locator(By.CSS_SELECTOR, '[data-test-testimonials-slide-1]')
    testimonial_2_slide = Locator(By.CSS_SELECTOR, '[data-test-testimonials-slide-2]')
    testimonial_3_slide = Locator(By.CSS_SELECTOR, '[data-test-testimonials-slide-3]')
    previous_testimonial_arrow = Locator(By.CSS_SELECTOR, '[data-test-previous-arrow]')
    next_testimonial_arrow = Locator(By.CSS_SELECTOR, '[data-test-next-arrow]')

    testimonial_buttons = GroupLocator(By.CSS_SELECTOR, '[data-test-navigation-item]')
    testimonial_view_research_links = GroupLocator(
        By.CSS_SELECTOR, '[data-analytics-name="View research"]'
    )

    # Components
    navbar = ComponentLocator(EmberNavbar)
    sign_up_form = ComponentLocator(SignUpForm)
