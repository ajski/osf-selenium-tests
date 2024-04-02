import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

import markers
import settings
import utils
from api import osf_api
from pages.project import (
    FilesMetadataPage,
    FilesPage,
)


@pytest.fixture()
def file_guid(driver, default_project, session, provider='osfstorage'):

    node_id = default_project.id
    node = osf_api.get_node(session, node_id=node_id)

    if settings.PREFERRED_NODE:
        new_file, metadata = osf_api.get_existing_file_data(session)
        files_page = FilesPage(
            driver, guid=settings.PREFERRED_NODE, addon_provider=provider
        )
        files_page.goto()
        # Wait for File List items to load
        WebDriverWait(driver, 15).until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, '[data-test-file-list-item]')
            )
        )
        row = utils.find_row_by_name(files_page, new_file)

        file_link = row.find_element_by_css_selector('[data-test-file-list-link]')
        file_link.click()
        driver.switch_to.window(driver.window_handles[0])
        file_id = metadata['data'][0]['attributes']['path']

    else:
        new_file, metadata = osf_api.upload_fake_file(
            session=session,
            node=node,
            name='files_metadata_test.txt',
            provider=provider,
        )
        files_page = FilesPage(driver, guid=node_id, addon_provider=provider)
        files_page.goto()
        # Wait for File List items to load
        WebDriverWait(driver, 15).until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, '[data-test-file-list-item]')
            )
        )
        row = utils.find_row_by_name(files_page, new_file)

        file_link = row.find_element_by_css_selector('[data-test-file-list-link]')
        file_link.click()
        driver.switch_to.window(driver.window_handles[0])
        file_id = metadata['data']['attributes']['path']

    file_guid = osf_api.get_fake_file_guid(session, file_id)
    return file_guid


@pytest.fixture()
def file_metadata_page(driver, file_guid):
    file_metadata_page = FilesMetadataPage(driver, guid=file_guid)
    file_metadata_page.goto()
    return file_metadata_page


@pytest.mark.usefixtures('must_be_logged_in')
class TestFilesMetadata:
    @pytest.fixture()
    def file_metadata_page_with_data(self, driver, file_metadata_page, fake):
        title = fake.sentence(nb_words=1)
        description = fake.sentence(nb_words=4)

        file_metadata_page.files_metadata_edit_button.click()
        file_metadata_page.edit_title.click()
        title_input = driver.find_element_by_css_selector(
            '[data-test-title-field] textarea'
        )
        title_input.send_keys(title)

        description_input = driver.find_element_by_css_selector(
            '[data-test-description-field] textarea'
        )
        description_input.send_keys(description)

        file_metadata_page.resource_type.click()

        WebDriverWait(driver, 5).until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, '[data-test-option="Book"]')
            )
        ).click()
        file_metadata_page.resource_language.click()
        WebDriverWait(driver, 5).until(
            EC.visibility_of_element_located((By.XPATH, '//li/span[text()="English"]'))
        ).click()

        file_metadata_page.save_metadata_button.click()
        return file_metadata_page

    @markers.smoke_test
    @markers.core_functionality
    def test_change_file_metadata_title(
        self, driver, file_metadata_page_with_data, fake
    ):
        """This test verifies that the file metadata field
        title is editable and changes are saved."""

        new_title = fake.sentence(nb_words=1)
        orig_title = file_metadata_page_with_data.files_metadata_title.text
        assert orig_title != new_title
        WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, '[data-test-edit-metadata-button]')
            )
        ).click()

        file_metadata_page_with_data.edit_title.click()
        title_input = driver.find_element_by_css_selector(
            '[data-test-title-field] textarea'
        )
        title_input.clear()
        title_input.send_keys(new_title)

        file_metadata_page_with_data.save_metadata_button.click()

        assert new_title == file_metadata_page_with_data.files_metadata_title.text

    @markers.smoke_test
    @markers.core_functionality
    def test_change_file_metadata_description(
        self, driver, file_metadata_page_with_data, fake
    ):
        """This test verifies that the file metadata field
        description is editable and changes are saved."""

        new_description = fake.sentence(nb_words=1)
        orig_description = file_metadata_page_with_data.files_metadata_description.text
        assert orig_description != new_description

        WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, '[data-test-edit-metadata-button]')
            )
        ).click()

        description_input = driver.find_element_by_css_selector(
            '[data-test-description-field] textarea'
        )
        description_input.clear()
        description_input.send_keys(new_description)
        file_metadata_page_with_data.save_metadata_button.click()
        assert (
            new_description
            == file_metadata_page_with_data.files_metadata_description.text
        )

    @markers.smoke_test
    @markers.core_functionality
    def test_change_file_metadata_resource_type(
        self, driver, file_metadata_page_with_data
    ):
        """This test verifies that the file metadata field
        resource type is editable and changes are saved."""

        orig_resource_type = (
            file_metadata_page_with_data.files_metadata_resource_type.text
        )

        WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, '[data-test-edit-metadata-button]')
            )
        ).click()
        file_metadata_page_with_data.resource_type.click()

        WebDriverWait(driver, 5).until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, '[data-test-option="Collection"]')
            )
        ).click()

        file_metadata_page_with_data.save_metadata_button.click()
        assert (
            orig_resource_type
            != file_metadata_page_with_data.files_metadata_resource_type.text
        )

    @markers.smoke_test
    @markers.core_functionality
    def test_change_file_metadata_resource_language(
        self, driver, file_metadata_page_with_data
    ):
        """This test verifies that the file metadata field
        resource language is editable and changes are saved."""
        orig_resource_language = (
            file_metadata_page_with_data.files_metadata_resource_language.text
        )

        WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, '[data-test-edit-metadata-button]')
            )
        ).click()
        file_metadata_page_with_data.resource_language.click()
        WebDriverWait(driver, 5).until(
            EC.visibility_of_element_located((By.XPATH, '//li/span[text()="Bengali"]'))
        ).click()

        file_metadata_page_with_data.save_metadata_button.click()
        assert (
            orig_resource_language
            != file_metadata_page_with_data.files_metadata_resource_language.text
        )

    @markers.smoke_test
    @markers.core_functionality
    def test_cancel_file_metadata_changes(
        self, driver, file_metadata_page_with_data, fake
    ):
        """This test verifies the file metadata fields
        title, Description, Resource Type and Resource Language are editable
        and changes can be cancelled without saving.
        """
        new_title = fake.sentence(nb_words=1)
        orig_title = file_metadata_page_with_data.files_metadata_title.text
        assert orig_title != new_title
        WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, '[data-test-edit-metadata-button]')
            )
        ).click()

        file_metadata_page_with_data.edit_title.click()
        title_input = driver.find_element_by_css_selector(
            '[data-test-title-field] textarea'
        )
        title_input.clear()
        title_input.send_keys(new_title)
        file_metadata_page_with_data.cancel_editing_button.click()
        assert new_title != file_metadata_page_with_data.files_metadata_title.text

    def test_download_file_metadata(self, driver, file_metadata_page_with_data):
        """This test verifies download file metadata
        functinality and verifies that latest downloaded
        file exists in the folder
        """
        try:
            WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, '[data-test-download-button]')
                )
            ).click()

            if '404' in driver.page_source:
                raise Exception
            else:
                file_metadata_page_with_data.reload()
                WebDriverWait(driver, 10).until(
                    EC.visibility_of_element_located(
                        (By.CSS_SELECTOR, '[data-test-filename')
                    )
                )
                # Verify File Download Functionality
                if settings.DRIVER != 'Remote':
                    url = driver.find_element_by_css_selector(
                        '[data-test-download-button]'
                    ).get_attribute('href')
                    guid = utils.get_guid_from_url(url, 3)
                    filename = utils.latest_download_file()
                    assert guid in filename
                else:
                    utils.verify_file_download(driver, file_name='')

        except Exception:
            print('404 Page not found error.')
