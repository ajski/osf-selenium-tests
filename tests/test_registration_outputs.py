import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

import markers
from api import osf_api
from pages.registries import RegistrationDetailPage


@pytest.mark.usefixtures('must_be_logged_in_as_registration_user')
@markers.dont_run_on_prod
@markers.core_functionality
class TestRegistrationOutputs:
    @pytest.fixture()
    def registration_guid(self, session):
        registration_guid = osf_api.get_registration_by_title(
            'Selenium Registration For Outputs Testing'
        )
        return registration_guid

    @pytest.fixture()
    def registration_details_page(self, driver, registration_guid):
        registration_details_page = RegistrationDetailPage(
            driver, guid=registration_guid
        )
        registration_details_page.goto()
        return registration_details_page

    def create_new_resource(
        self, driver, registration_guid, registration_details_page, resource_type
    ):
        """This method creates new resource of the type given for the given registration"""
        doi = '10.17605'
        registration_details_page.add_resource_button.click()
        registration_details_page.doi_input_field.clear()
        registration_details_page.doi_input_field.click()
        registration_details_page.doi_input_field.send_keys(doi)

        # Select 'Data' from the resource type listbox
        registration_details_page.resource_type_dropdown.click()

        registration_details_page.select_from_dropdown_listbox(resource_type)
        registration_details_page.preview_button.click()
        registration_details_page.resource_type_add_button.click()

    def test_add_new_resource_data(
        self, driver, registration_details_page, registration_guid
    ):
        """This test verifies adding new Data output resource for a registration
        and verifies that the Data icon color changes when resource is added"""
        registration_details_page.open_practice_resource_data.click()
        WebDriverWait(driver, 5).until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, '[data-test-add-resource-section]')
            )
        )
        # Verify if resource already exists and delete the resource if already exists
        resource_id = osf_api.get_registration_resource_id(
            registration_id=registration_guid
        )
        if resource_id is not None:
            osf_api.delete_registration_resource(registration_guid)
            registration_details_page.reload()
            WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located(
                    (By.CSS_SELECTOR, '[data-test-add-resource-section]')
                )
            )

        orig_data_icon_color = driver.find_element_by_css_selector(
            'img[data-analytics-name="data"]'
        ).get_attribute('src')
        self.create_new_resource(
            self, driver, registration_details_page, resource_type='Data'
        )

        registration_details_page.reload()
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, '[data-test-add-resource-section]')
            )
        )
        new_data_icon_color = driver.find_element_by_css_selector(
            'img[data-analytics-name="data"]'
        ).get_attribute('src')
        assert new_data_icon_color != orig_data_icon_color
        osf_api.delete_registration_resource(registration_guid)

    def test_edit_resource_data(
        self, driver, registration_details_page, registration_guid, fake
    ):
        """This test updates the description of data output resource for a given registration"""
        resource_description = fake.sentence(nb_words=1)
        registration_details_page.open_practice_resource_data.click()
        # Verify n and delete the resource if already exists
        resource_id = osf_api.get_registration_resource_id(
            registration_id=registration_guid
        )
        if resource_id is not None:
            osf_api.delete_registration_resource(registration_guid)
            registration_details_page.reload()
            WebDriverWait(driver, 5).until(
                EC.visibility_of_element_located(
                    (By.CSS_SELECTOR, '[data-test-add-resource-section]')
                )
            )

        osf_api.create_registration_resource(registration_guid, resource_type='Data')
        registration_details_page.reload()
        WebDriverWait(driver, 5).until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, '[data-test-add-resource-section]')
            )
        )
        registration_details_page.resource_type_edit_button.click()
        registration_details_page.resource_description.click()
        registration_details_page.resource_description.clear()
        registration_details_page.resource_description.send_keys(resource_description)
        registration_details_page.save_button.click()

        registration_details_page.reload()
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, '[data-test-add-resource-section]')
            )
        )
        assert (
            registration_details_page.resource_card_description.text
            == resource_description
        )
        osf_api.delete_registration_resource(registration_guid)

    def test_delete_resource_data(
        self, driver, registration_details_page, registration_guid, fake
    ):
        """This test verifies delete functionality of data output resource for a registration"""

        registration_details_page.open_practice_resource_data.click()
        # Verify and delete the resource if already exists
        resource_id = osf_api.get_registration_resource_id(
            registration_id=registration_guid
        )
        if resource_id is not None:
            osf_api.delete_registration_resource(registration_guid)
            registration_details_page.reload()
            WebDriverWait(driver, 5).until(
                EC.visibility_of_element_located(
                    (By.CSS_SELECTOR, '[data-test-add-resource-section]')
                )
            )

        osf_api.create_registration_resource(registration_guid, resource_type='Data')
        registration_details_page.reload()
        WebDriverWait(driver, 5).until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, '[data-test-add-resource-section]')
            )
        )

        orig_data_icon_color = driver.find_element_by_css_selector(
            'img[data-analytics-name="data"]'
        ).get_attribute('src')
        registration_details_page.resource_type_delete_button.click()
        registration_details_page.resource_type_delete_confirm.click()
        registration_details_page.reload()
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, '[data-test-add-resource-section]')
            )
        )
        new_data_icon_color = driver.find_element_by_css_selector(
            'img[data-analytics-name="data"]'
        ).get_attribute('src')
        assert new_data_icon_color != orig_data_icon_color
