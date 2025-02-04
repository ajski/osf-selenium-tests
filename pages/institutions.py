import ipdb
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

import settings
from base.locators import (
    ComponentLocator,
    GroupLocator,
    Locator,
)
from components.navbars import InstitutionsNavbar
from pages.base import OSFBasePage


class InstitutionsLandingPage(OSFBasePage):
    url = settings.OSF_HOME + '/institutions/'

    # TODO fix insitution typo
    identity = Locator(
        By.CSS_SELECTOR, 'div[data-test-insitutions-header]', settings.VERY_LONG_TIMEOUT
    )

    search_bar = Locator(By.CSS_SELECTOR, '.ember-text-field')

    # Group Locators
    institution_list = GroupLocator(By.CSS_SELECTOR, 'div[data-test-institution-name]')

    navbar = ComponentLocator(InstitutionsNavbar)


class BaseInstitutionPage(OSFBasePage):

    base_url = settings.OSF_HOME + '/institutions/'
    url_addition = ''

    def __init__(self, driver, verify=False, institution_id=''):
        self.institution_id = institution_id
        super().__init__(driver, verify)

    @property
    def url(self):
        return self.base_url + self.institution_id + self.url_addition


class InstitutionBrandedPage(BaseInstitutionPage):

    identity = Locator(By.CSS_SELECTOR, 'img[data-test-institution-banner]')

    empty_collection_indicator = Locator(
        By.CLASS_NAME, 'div[class="_no-results_fvrbco"]'
    )

    # Group Locators
    project_list = GroupLocator(
        By.CSS_SELECTOR, 'a[data-test-search-result-card-title]'
    )


class InstitutionAdminDashboardPage(BaseInstitutionPage):

    url_addition = '/dashboard'

    identity = Locator(By.CSS_SELECTOR, '._institution-banner_kv000k')
    loading_indicator = Locator(By.CSS_SELECTOR, '.ball-scale ball-dark _LoadingIndicator_k6n1c2', settings.LONG_TIMEOUT)
    title_containers = GroupLocator(
        By.CSS_SELECTOR,
        '._title-container_1d9vmx',
    )
    total_project_count = GroupLocator(
        By.CSS_SELECTOR,
        '._kpi-container_1ge2xx',
    )
    public_project_count = Locator(
        By.CSS_SELECTOR, 'div._projects-count_1ky9tx > span:nth-child(1) > strong'
    )
    private_project_count = Locator(
        By.CSS_SELECTOR, 'div._projects-count_1ky9tx > span:nth-child(2) > strong'
    )
    department_options = GroupLocator(
        By.CSS_SELECTOR, 'ul._data-list_1d9vmx > li._data-container_1d9vmx'
    )
    user_table_rows = GroupLocator(
        By.CSS_SELECTOR,
        'div._table-wrapper_1w5vdt > div > div.ember-view > div > div > table > tbody > tr',
    )

    def select_department_from_listbox(self, department):
        for element in  self.department_options:
            name_elem = element.find_element(By.CSS_SELECTOR, "div._name_1d9vmx")
            if name_elem.text.strip() ==  department:
                total_elem = element.find_element(By.CSS_SELECTOR, "div._total_1d9vmx")
                return int(total_elem.text.strip())

    def get_total_count_by_kpi_title(self, target_title):
        for container in self.total_project_count:
            title_element = container.find_element(By.CSS_SELECTOR, "._title_1ge2xx")
            if title_element.text.strip() == target_title:
                value_element = container.find_element(By.CSS_SELECTOR, "._total-container_1ge2xx")
                return value_element.text.strip()

    def click_on_listbox_trigger(self, section_title):
        for section in self.title_containers:
            title_element = section.find_element(By.CSS_SELECTOR, "._title_1d9vmx")
            if title_element.text.strip() == section_title:
                button = section.find_element(By.CSS_SELECTOR, "button._Button_6kisxq._FakeLink_6kisxq")
                icon = section.find_element(By.CSS_SELECTOR, "[data-test-toggle-icon]")
                button.click()
                WebDriverWait(self.driver, 10).until(
                    lambda d: icon.get_attribute("data-icon") == "caret-up"
                )

