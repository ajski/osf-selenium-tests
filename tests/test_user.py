import os
import re

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

import markers
import settings
from api import osf_api
from pages import user


@pytest.fixture
def user_one_profile_page(driver):
    profile_page = user.UserProfilePage(driver)
    return profile_page


class ProfilePageMixin:
    """Mixin used to inject generic tests"""

    @pytest.fixture()
    def profile_page(self, driver):
        raise NotImplementedError()

    @markers.smoke_test
    @markers.core_functionality
    def test_nothings_public(self, profile_page):
        """Confirm that the user has no public projects."""
        profile_page.loading_indicator.here_then_gone()
        assert profile_page.no_public_projects_text.present()
        assert profile_page.no_public_components_text.present()

    @markers.dont_run_on_prod
    @markers.core_functionality
    def test_public_lists(self, public_project, profile_page):
        profile_page.loading_indicator.here_then_gone()
        assert profile_page.public_projects


class TestProfileLoggedIn(ProfilePageMixin):
    @pytest.fixture()
    def profile_page(self, user_one_profile_page, must_be_logged_in):
        user_one_profile_page.goto()
        return user_one_profile_page


class TestProfileLoggedOut(ProfilePageMixin):
    @pytest.fixture()
    def profile_page(self, user_one_profile_page):
        user_one_profile_page.goto()
        return user_one_profile_page


class TestProfileAsDifferentUser(ProfilePageMixin):
    @pytest.fixture()
    def profile_page(self, user_one_profile_page, must_be_logged_in_as_user_two):
        user_one_profile_page.goto()
        return user_one_profile_page


@pytest.mark.usefixtures('must_be_logged_in')
class TestUserSettings:
    @pytest.fixture(
        params=[
            user.ProfileInformationPage,
            user.AccountSettingsPage,
            user.ConfigureAddonsPage,
            user.NotificationsPage,
            user.DeveloperAppsPage,
            user.PersonalAccessTokenPage,
        ]
    )
    def settings_page(self, request, driver):
        """Run any test using this fixture with each user settings page individually."""
        settings_page = request.param(driver)
        return settings_page

    @pytest.fixture()
    def profile_settings_page(self, driver):
        profile_settings_page = user.ProfileInformationPage(driver)
        profile_settings_page.goto()
        return profile_settings_page

    @markers.smoke_test
    @markers.core_functionality
    def test_user_settings_loads(self, settings_page):
        """Confirm the given user settings page loads."""
        settings_page.goto()

    @markers.core_functionality
    def test_change_middle_name(self, driver, profile_settings_page, fake):
        new_name = fake.name()
        assert (
            profile_settings_page.middle_name_input.get_attribute('value') != new_name
        )
        profile_settings_page.middle_name_input.clear()
        profile_settings_page.middle_name_input.send_keys(new_name)
        profile_settings_page.save_button.click()
        profile_settings_page.update_success.here_then_gone()
        profile_settings_page.reload()
        assert WebDriverWait(driver, 10).until(
            EC.text_to_be_present_in_element_value(
                (By.CSS_SELECTOR, '#names > div > form > div:nth-child(5) > input'),
                new_name,
            )
        )


@markers.dont_run_on_prod
@pytest.mark.usefixtures('must_be_logged_in')
class TestUserDeveloperApps:
    def test_user_settings_create_dev_app(self, driver, session, fake):
        """Create a Developer Application from the User Settings Developer Apps page
        in OSF. The test uses the OSF api to delete the developer app at the end of the
        test as cleanup.
        """
        dev_apps_page = user.DeveloperAppsPage(driver)
        dev_apps_page.goto()
        assert user.DeveloperAppsPage(driver, verify=True)
        dev_apps_page.create_dev_app_button.click()
        create_page = user.CreateDeveloperAppPage(driver, verify=True)

        # Complete the form fields and click the Create developer app button
        app_name = fake.sentence(nb_words=3)
        create_page.app_name_input.send_keys(app_name)
        create_page.project_url_input.send_keys(settings.OSF_HOME)
        create_page.app_description_textarea.click()
        create_page.app_description_textarea.send_keys(
            'Selenium test: ' + os.environ['PYTEST_CURRENT_TEST']
        )
        create_page.callback_url_input.send_keys('https://www.google.com/')
        create_page.create_dev_app_button.click()
        try:
            # Verify that you are now on the Edit page for the newly created Developer
            # app
            edit_page = user.EditDeveloperAppPage(driver, verify=True)
            edit_page.loading_indicator.here_then_gone()

            # Get client id from the input box and verify that it is also in the page's
            # url
            client_id = edit_page.client_id_input.get_attribute('value')
            assert client_id in driver.current_url

            # Verify other info on this page - we need to use up 2 minutes before
            # attempting to delete the dev app using the api, since CAS only refreshes
            # its db connection every 2 minutes.
            edit_page.show_client_secret_button.click()
            # Get the dev app data from the api and verify client secret
            dev_app_data = osf_api.get_user_developer_app_data(
                session, app_id=client_id
            )
            client_secret = dev_app_data['attributes']['client_secret']
            assert edit_page.client_secret_input.get_attribute('value') == client_secret
            edit_page.scroll_into_view(edit_page.app_name_input.element)
            assert edit_page.app_name_input.get_attribute('value') == app_name
            edit_page.scroll_into_view(edit_page.project_url_input.element)
            assert (
                edit_page.project_url_input.get_attribute('value') == settings.OSF_HOME
            )
            edit_page.scroll_into_view(edit_page.app_description_textarea.element)
            assert (
                edit_page.app_description_textarea.get_attribute('value')
                == 'Selenium test: ' + os.environ['PYTEST_CURRENT_TEST']
            )
            edit_page.scroll_into_view(edit_page.callback_url_input.element)
            assert (
                edit_page.callback_url_input.get_attribute('value')
                == 'https://www.google.com/'
            )

            # Click the Save button to go back to the Dev Apps list page
            edit_page.scroll_into_view(edit_page.save_button.element)
            edit_page.save_button.click()
            dev_apps_page = user.DeveloperAppsPage(driver, verify=True)
            dev_apps_page.loading_indicator.here_then_gone()

            # Go through the list of developer apps listed on the page to find the one
            # that was just added
            dev_app_card = dev_apps_page.get_dev_app_card_by_app_name(app_name)
            app_link = dev_app_card.find_element_by_css_selector('a')
            link_url = app_link.get_attribute('href')
            link_client_id = link_url.split('applications/', 1)[1]
            assert link_client_id == client_id

            # Now click the app name link to go back to Edit Dev App page and verify
            # the data again - just trying to waste more time before we can delete
            # the app
            app_link.click()
            edit_page = user.EditDeveloperAppPage(driver, verify=True)
            edit_page.loading_indicator.here_then_gone()

            # Click the Show client secret button to unveil the client secret and verify
            # the text on the button has changed to 'Hide client secret'
            edit_page.show_client_secret_button.click()
            assert edit_page.show_client_secret_button.text == 'Hide client secret'
            assert edit_page.client_secret_input.get_attribute('value') == client_secret
            edit_page.scroll_into_view(edit_page.app_name_input.element)
            assert edit_page.app_name_input.get_attribute('value') == app_name
            edit_page.scroll_into_view(edit_page.project_url_input.element)
            assert (
                edit_page.project_url_input.get_attribute('value') == settings.OSF_HOME
            )
            edit_page.scroll_into_view(edit_page.app_description_textarea.element)
            assert (
                edit_page.app_description_textarea.get_attribute('value')
                == 'Selenium test: ' + os.environ['PYTEST_CURRENT_TEST']
            )
            edit_page.scroll_into_view(edit_page.callback_url_input.element)
            assert (
                edit_page.callback_url_input.get_attribute('value')
                == 'https://www.google.com/'
            )
            edit_page.scroll_into_view(edit_page.save_button.element)
            edit_page.save_button.click()
            dev_apps_page = user.DeveloperAppsPage(driver, verify=True)
            dev_apps_page.loading_indicator.here_then_gone()
        finally:
            # Lastly use the api to delete the dev app as cleanup
            osf_api.delete_user_developer_app(session, app_id=client_id)

    def test_user_settings_delete_dev_app(self, driver, session, fake):
        """Delete a Developer Application from the User Settings Developer Apps page
        in OSF. The test uses the OSF api to first create the developer application that
        will then be deleted using the Front End interface.
        """
        app_name = 'Dev App via api ' + fake.sentence(nb_words=1)
        app_id = osf_api.create_user_developer_app(
            session,
            name=app_name,
            description='a developer application created using the OSF api',
            home_url=settings.OSF_HOME,
            callback_url='https://www.google.com/',
        )

        # Note: We need to use up 2 minutes before attempting to delete the dev app
        # since CAS only refreshes its db connection every 2 minutes.
        try:
            # Go to the Profile Information page first and use the side navigation bar
            # to then go to the Developer Apps page.
            profile_settings_page = user.ProfileInformationPage(driver)
            profile_settings_page.goto()
            assert user.ProfileInformationPage(driver, verify=True)
            profile_settings_page.side_navigation.developer_apps_link.click()
            dev_apps_page = user.DeveloperAppsPage(driver, verify=True)
            dev_apps_page.loading_indicator.here_then_gone()

            # Go through the list of developer apps listed on the page to find the one
            # that was just added via the api
            dev_app_card = dev_apps_page.get_dev_app_card_by_app_name(app_name)
            app_link = dev_app_card.find_element_by_css_selector('a')
            link_url = app_link.get_attribute('href')
            link_client_id = link_url.split('applications/', 1)[1]
            assert link_client_id == app_id

            # Now click the app name link to go to the Edit Dev App page and verify the
            # data
            app_link.click()
            edit_page = user.EditDeveloperAppPage(driver, verify=True)
            edit_page.loading_indicator.here_then_gone()

            # Verify that the app_id is also in the page's url
            assert app_id in driver.current_url
            assert edit_page.client_id_input.get_attribute('value') == app_id
            edit_page.show_client_secret_button.click()

            # Get the dev app data from the api and verify client secret
            dev_app_data = osf_api.get_user_developer_app_data(session, app_id=app_id)
            client_secret = dev_app_data['attributes']['client_secret']
            assert edit_page.client_secret_input.get_attribute('value') == client_secret
            edit_page.scroll_into_view(edit_page.app_name_input.element)
            assert edit_page.app_name_input.get_attribute('value') == app_name
            edit_page.scroll_into_view(edit_page.project_url_input.element)
            assert (
                edit_page.project_url_input.get_attribute('value') == settings.OSF_HOME
            )
            edit_page.scroll_into_view(edit_page.app_description_textarea.element)
            assert (
                edit_page.app_description_textarea.get_attribute('value')
                == 'a developer application created using the OSF api'
            )
            edit_page.scroll_into_view(edit_page.callback_url_input.element)
            assert (
                edit_page.callback_url_input.get_attribute('value')
                == 'https://www.google.com/'
            )

            # Note: The Delete button on the Edit Dev App page does not actually do
            # anything - this is a known bug. So click the Save button to go back to
            # the Dev Apps List page and delete the app from there.
            edit_page.scroll_into_view(edit_page.save_button.element)
            edit_page.save_button.click()
            dev_apps_page = user.DeveloperAppsPage(driver, verify=True)
            dev_apps_page.loading_indicator.here_then_gone()
            dev_app_card = dev_apps_page.get_dev_app_card_by_app_name(app_name)
            delete_button = dev_app_card.find_element_by_css_selector(
                '[data-test-delete-button]'
            )
            delete_button.click()

            # Verify the Delete Dev App Modal is displayed
            delete_modal = dev_apps_page.delete_dev_app_modal
            assert delete_modal.app_name.text == app_name

            # Click the Cancel button first and verify that the Dev App is not
            # actually deleted
            delete_modal.cancel_button.click()
            dev_apps_page.reload()
            dev_apps_page = user.DeveloperAppsPage(driver, verify=True)
            dev_apps_page.loading_indicator.here_then_gone()

            # Find the Dev App card again and click the Delete button again
            dev_app_card = dev_apps_page.get_dev_app_card_by_app_name(app_name)
            delete_button = dev_app_card.find_element_by_css_selector(
                '[data-test-delete-button]'
            )
            delete_button.click()
            delete_modal = dev_apps_page.delete_dev_app_modal
            assert delete_modal.app_name.text == app_name

            # This time click the Delete button to actually delete the Dev App
            delete_modal.delete_button.click()
            dev_apps_page.reload()
            dev_apps_page = user.DeveloperAppsPage(driver, verify=True)
            dev_apps_page.loading_indicator.here_then_gone()
            dev_app_card = dev_apps_page.get_dev_app_card_by_app_name(app_name)

            # Verify that we don't find the dev app card this time since it was deleted
            assert not dev_app_card
        except Exception:
            # As cleanup, delete the dev app using the api if the test failed for some
            # reason and the dev app was not actually deleted.
            dev_app_data = osf_api.get_user_developer_app_data(session, app_id=app_id)
            if dev_app_data:
                osf_api.delete_user_developer_app(session, app_id=app_id)

    def test_user_settings_edit_dev_app(self, driver, session, fake):
        """Edit a Developer Application from the User Settings Developer Apps page
        in OSF. The test uses the OSF api to first create the developer application that
        will then be edited using the Front End interface. After the test is complete
        the developer app will then be deleted using the OSF api as cleanup.
        """
        app_name = 'Dev App via api ' + fake.sentence(nb_words=1)
        app_id = osf_api.create_user_developer_app(
            session,
            name=app_name,
            description='a developer application created using the OSF api',
            home_url=settings.OSF_HOME,
            callback_url='https://www.google.com/',
        )

        # Note: We need to use up 2 minutes before attempting to delete the dev app
        # since CAS only refreshes its db connection every 2 minutes.
        try:
            # Go to the Profile Information page first and use the side navigation bar
            # to then go to the Developer Apps page.
            profile_settings_page = user.ProfileInformationPage(driver)
            profile_settings_page.goto()
            assert user.ProfileInformationPage(driver, verify=True)
            profile_settings_page.side_navigation.developer_apps_link.click()
            dev_apps_page = user.DeveloperAppsPage(driver, verify=True)
            dev_apps_page.loading_indicator.here_then_gone()

            # Go through the list of developer apps listed on the page to find the one
            # that was just added via the api
            dev_app_card = dev_apps_page.get_dev_app_card_by_app_name(app_name)
            app_link = dev_app_card.find_element_by_css_selector('a')
            link_url = app_link.get_attribute('href')
            link_client_id = link_url.split('applications/', 1)[1]
            assert link_client_id == app_id

            # Now click the app name link to go to the Edit Dev App page and verify the
            # data
            app_link.click()
            edit_page = user.EditDeveloperAppPage(driver, verify=True)
            edit_page.loading_indicator.here_then_gone()

            # Verify that the app_id is also in the page's url
            assert app_id in driver.current_url
            assert edit_page.client_id_input.get_attribute('value') == app_id
            edit_page.show_client_secret_button.click()

            # Get the dev app data from the api and verify client secret
            dev_app_data = osf_api.get_user_developer_app_data(session, app_id=app_id)
            client_secret = dev_app_data['attributes']['client_secret']
            assert edit_page.client_secret_input.get_attribute('value') == client_secret
            edit_page.scroll_into_view(edit_page.app_name_input.element)
            assert edit_page.app_name_input.get_attribute('value') == app_name
            edit_page.scroll_into_view(edit_page.project_url_input.element)
            assert (
                edit_page.project_url_input.get_attribute('value') == settings.OSF_HOME
            )
            edit_page.scroll_into_view(edit_page.app_description_textarea.element)
            assert (
                edit_page.app_description_textarea.get_attribute('value')
                == 'a developer application created using the OSF api'
            )
            edit_page.scroll_into_view(edit_page.callback_url_input.element)
            assert (
                edit_page.callback_url_input.get_attribute('value')
                == 'https://www.google.com/'
            )

            # Now update some of the data fields and Save the changes
            new_app_name = app_name + ' edited'
            edit_page.app_name_input.clear()
            edit_page.app_name_input.send_keys_deliberately(new_app_name)
            edit_page.app_description_textarea.click()
            edit_page.app_description_textarea.send_keys_deliberately(' and edited')
            edit_page.scroll_into_view(edit_page.save_button.element)
            edit_page.save_button.click()
            dev_apps_page = user.DeveloperAppsPage(driver, verify=True)
            dev_apps_page.loading_indicator.here_then_gone()

            # Go through the list of developer apps listed on the page to find the one
            # that was just edited
            dev_app_card = dev_apps_page.get_dev_app_card_by_app_name(new_app_name)
            app_link = dev_app_card.find_element_by_css_selector('a')
            link_url = app_link.get_attribute('href')
            link_client_id = link_url.split('applications/', 1)[1]
            assert link_client_id == app_id

            # Now click the app name link to go back to Edit Dev App page and verify
            # the data again - just trying to waste more time before we can delete
            # the app
            app_link.click()
            edit_page = user.EditDeveloperAppPage(driver, verify=True)
            edit_page.loading_indicator.here_then_gone()

            # Click the Show client secret button to unveil the client secret and verify
            # the text on the button has changed to 'Hide client secret'
            edit_page.show_client_secret_button.click()
            assert edit_page.show_client_secret_button.text == 'Hide client secret'
            assert edit_page.client_secret_input.get_attribute('value') == client_secret
            edit_page.scroll_into_view(edit_page.app_name_input.element)
            assert edit_page.app_name_input.get_attribute('value') == new_app_name
            edit_page.scroll_into_view(edit_page.project_url_input.element)
            assert (
                edit_page.project_url_input.get_attribute('value') == settings.OSF_HOME
            )
            edit_page.scroll_into_view(edit_page.app_description_textarea.element)
            assert (
                edit_page.app_description_textarea.get_attribute('value')
                == 'a developer application created using the OSF api and edited'
            )
            edit_page.scroll_into_view(edit_page.callback_url_input.element)
            assert (
                edit_page.callback_url_input.get_attribute('value')
                == 'https://www.google.com/'
            )
            edit_page.scroll_into_view(edit_page.save_button.element)
            edit_page.save_button.click()
            dev_apps_page = user.DeveloperAppsPage(driver, verify=True)
            dev_apps_page.loading_indicator.here_then_gone()
            dev_app_card = dev_apps_page.get_dev_app_card_by_app_name(new_app_name)
            assert dev_app_card
        finally:
            # Lastly use the api to delete the dev app as cleanup
            osf_api.delete_user_developer_app(session, app_id=app_id)


@markers.dont_run_on_prod
@pytest.mark.usefixtures('must_be_logged_in')
class TestUserPersonalAccessTokens:
    def test_user_settings_create_PAT(self, driver, session, fake):
        """Create a Personal Access Token from the User Settings Personal Access Tokens
        page in OSF. The test uses the OSF api to delete the personal access token at
        the end of the test as cleanup.
        """
        pat_page = user.PersonalAccessTokenPage(driver)
        pat_page.goto()
        assert user.PersonalAccessTokenPage(driver, verify=True)
        pat_page.loading_indicator.here_then_gone()
        pat_page.create_token_button.click()
        create_page = user.CreatePersonalAccessTokenPage(driver, verify=True)

        try:
            # Complete the form fields and click the Create token button
            token_name = fake.sentence(nb_words=3)
            create_page.token_name_input.send_keys(token_name)

            # Check all the 'read' access checkboxes
            create_page.scroll_into_view(
                create_page.osf_nodes_full_read_checkbox.element
            )
            create_page.osf_nodes_full_read_checkbox.click()
            create_page.scroll_into_view(create_page.osf_full_read_checkbox.element)
            create_page.osf_full_read_checkbox.click()
            create_page.scroll_into_view(
                create_page.osf_nodes_metadata_read_checkbox.element
            )
            create_page.osf_nodes_metadata_read_checkbox.click()
            create_page.scroll_into_view(
                create_page.osf_nodes_access_read_checkbox.element
            )
            create_page.osf_nodes_access_read_checkbox.click()
            create_page.scroll_into_view(
                create_page.osf_nodes_data_read_checkbox.element
            )
            create_page.osf_nodes_data_read_checkbox.click()
            create_page.scroll_into_view(
                create_page.osf_users_email_read_checkbox.element
            )
            create_page.osf_users_email_read_checkbox.click()
            create_page.scroll_into_view(
                create_page.osf_users_profile_read_checkbox.element
            )
            create_page.osf_users_profile_read_checkbox.click()
            create_page.scroll_into_view(create_page.create_token_button.element)
            create_page.create_token_button.click()

            # Should end up on Token Detail page with newly created token displayed
            edit_page = user.EditPersonalAccessTokenPage(driver, verify=True)

            # Capture the token id from the url
            match = re.search(r'tokens/([a-z0-9]{24})\?view_only=', driver.current_url)
            token_id = match.group(1)

            # Verify that New Token Input Box has a value
            assert edit_page.new_token_input.get_attribute('value') != ''

            # Click the Back to list of tokens link
            edit_page.back_to_list_of_tokens_link.click()
            pat_page = user.PersonalAccessTokenPage(driver, verify=True)
            pat_page.loading_indicator.here_then_gone()

            # Go through the list of PATs listed on the page to find the one that was
            # just added
            pat_card = pat_page.get_pat_card_by_name(token_name)
            pat_link = pat_card.find_element_by_css_selector('a')
            link_url = pat_link.get_attribute('href')
            link_token_id = link_url.split('tokens/', 1)[1]
            assert link_token_id == token_id

            # Now click the PAT name link to go to the Edit PAT page and verify the
            # data
            pat_link.click()
            edit_page = user.EditPersonalAccessTokenPage(driver, verify=True)
            assert edit_page.token_name_input.get_attribute('value') == token_name
            edit_page.scroll_into_view(edit_page.osf_nodes_full_read_checkbox.element)
            assert edit_page.osf_nodes_full_read_checkbox.is_selected()
            edit_page.scroll_into_view(edit_page.osf_full_read_checkbox.element)
            assert edit_page.osf_full_read_checkbox.is_selected()
            edit_page.scroll_into_view(
                edit_page.osf_nodes_metadata_read_checkbox.element
            )
            assert edit_page.osf_nodes_metadata_read_checkbox.is_selected()
            edit_page.scroll_into_view(edit_page.osf_nodes_access_read_checkbox.element)
            assert edit_page.osf_nodes_access_read_checkbox.is_selected()
            edit_page.scroll_into_view(edit_page.osf_nodes_data_read_checkbox.element)
            assert edit_page.osf_nodes_data_read_checkbox.is_selected()
            edit_page.scroll_into_view(edit_page.osf_users_email_read_checkbox.element)
            assert edit_page.osf_users_email_read_checkbox.is_selected()
            edit_page.scroll_into_view(
                edit_page.osf_users_profile_read_checkbox.element
            )
            assert edit_page.osf_users_profile_read_checkbox.is_selected()
            edit_page.scroll_into_view(
                edit_page.osf_users_profile_write_checkbox.element
            )
            assert not edit_page.osf_users_profile_write_checkbox.is_selected()
            edit_page.scroll_into_view(edit_page.osf_full_write_checkbox.element)
            assert not edit_page.osf_full_write_checkbox.is_selected()
            edit_page.scroll_into_view(edit_page.osf_nodes_full_write_checkbox.element)
            assert not edit_page.osf_nodes_full_write_checkbox.is_selected()
            edit_page.scroll_into_view(
                edit_page.osf_nodes_metadata_write_checkbox.element
            )
            assert not edit_page.osf_nodes_metadata_write_checkbox.is_selected()
            edit_page.scroll_into_view(
                edit_page.osf_nodes_access_write_checkbox.element
            )
            assert not edit_page.osf_nodes_access_write_checkbox.is_selected()
            edit_page.scroll_into_view(edit_page.osf_nodes_data_write_checkbox.element)
            assert not edit_page.osf_nodes_data_write_checkbox.is_selected()
        finally:
            # Delete the token using the api as cleanup
            if token_id:
                osf_api.delete_personal_access_token(session, token_id=token_id)

    def test_user_settings_delete_PAT_from_edit_page(self, driver, session, fake):
        """Delete a Personal Access Token from the User Settings Edit Personal Access
        Token page in OSF. The test uses the OSF api to first create the personal access
        token that will then be deleted using the Front End interface.
        """
        token_name = 'PAT created via api ' + fake.sentence(nb_words=1)
        token_id = osf_api.create_personal_access_token(
            session,
            name=token_name,
            scopes='osf.nodes.full_read osf.nodes.metadata_read osf.nodes.access_read osf.nodes.data_read',
        )
        try:
            # Go to the Profile Information page first and use the side navigation bar
            # to then go to the Personal Access Tokens page.
            profile_settings_page = user.ProfileInformationPage(driver)
            profile_settings_page.goto()
            assert user.ProfileInformationPage(driver, verify=True)
            profile_settings_page.side_navigation.personal_access_tokens_link.click()
            pat_page = user.PersonalAccessTokenPage(driver, verify=True)
            pat_page.loading_indicator.here_then_gone()

            # Go through the list of PATs listed on the page to find the one that was
            # just added via the api
            pat_card = pat_page.get_pat_card_by_name(token_name)
            pat_link = pat_card.find_element_by_css_selector('a')
            link_url = pat_link.get_attribute('href')
            link_token_id = link_url.split('tokens/', 1)[1]
            assert link_token_id == token_id

            # Now click the PAT name link to go to the Edit PAT page and verify the
            # data
            pat_link.click()
            edit_page = user.EditPersonalAccessTokenPage(driver, verify=True)
            assert edit_page.token_name_input.get_attribute('value') == token_name
            edit_page.scroll_into_view(edit_page.osf_nodes_full_read_checkbox.element)
            assert edit_page.osf_nodes_full_read_checkbox.is_selected()
            edit_page.scroll_into_view(
                edit_page.osf_nodes_metadata_read_checkbox.element
            )
            assert edit_page.osf_nodes_metadata_read_checkbox.is_selected()
            edit_page.scroll_into_view(edit_page.osf_nodes_access_read_checkbox.element)
            assert edit_page.osf_nodes_access_read_checkbox.is_selected()
            edit_page.scroll_into_view(edit_page.osf_nodes_data_read_checkbox.element)
            assert edit_page.osf_nodes_data_read_checkbox.is_selected()
            edit_page.scroll_into_view(
                edit_page.osf_users_profile_write_checkbox.element
            )
            assert not edit_page.osf_users_profile_write_checkbox.is_selected()
            edit_page.scroll_into_view(edit_page.osf_full_write_checkbox.element)
            assert not edit_page.osf_full_write_checkbox.is_selected()
            edit_page.scroll_into_view(
                edit_page.osf_nodes_metadata_write_checkbox.element
            )
            assert not edit_page.osf_nodes_metadata_write_checkbox.is_selected()
            edit_page.scroll_into_view(edit_page.osf_full_read_checkbox.element)
            assert not edit_page.osf_full_read_checkbox.is_selected()
            edit_page.scroll_into_view(edit_page.osf_nodes_full_write_checkbox.element)
            assert not edit_page.osf_nodes_full_write_checkbox.is_selected()
            edit_page.scroll_into_view(
                edit_page.osf_nodes_access_write_checkbox.element
            )
            assert not edit_page.osf_nodes_access_write_checkbox.is_selected()
            edit_page.scroll_into_view(edit_page.osf_nodes_data_write_checkbox.element)
            assert not edit_page.osf_nodes_data_write_checkbox.is_selected()
            edit_page.scroll_into_view(edit_page.osf_users_email_read_checkbox.element)
            assert not edit_page.osf_users_email_read_checkbox.is_selected()
            edit_page.scroll_into_view(
                edit_page.osf_users_profile_read_checkbox.element
            )
            assert not edit_page.osf_users_profile_read_checkbox.is_selected()

            # Click the Delete button
            edit_page.scroll_into_view(edit_page.delete_button.element)
            edit_page.delete_button.click()

            # On the Delete Token modal - first click the Cancel button
            delete_modal = edit_page.delete_pat_modal
            assert delete_modal.token_name.text == token_name
            delete_modal.cancel_button.click()

            # Should still be on the Edit page
            assert user.EditPersonalAccessTokenPage(driver, verify=True)

            # Go back to the Personal Access Tokens list page to make sure the PAT is
            # still there
            pat_page = user.PersonalAccessTokenPage(driver)
            pat_page.goto()
            assert user.PersonalAccessTokenPage(driver, verify=True)
            pat_page.loading_indicator.here_then_gone()
            pat_card = pat_page.get_pat_card_by_name(token_name)
            assert pat_card
            pat_link = pat_card.find_element_by_css_selector('a')

            # Now click the PAT name link again to go back to the Edit PAT page
            pat_link.click()
            edit_page = user.EditPersonalAccessTokenPage(driver, verify=True)
            assert edit_page.token_name_input.get_attribute('value') == token_name

            # Click the Delete button again and this time click the Delete button on the
            # Delete Token Modal
            edit_page.scroll_into_view(edit_page.delete_button.element)
            edit_page.delete_button.click()
            delete_modal = edit_page.delete_pat_modal
            assert delete_modal.token_name.text == token_name
            delete_modal.delete_button.click()

            # This time we should end up on the PAT list page
            pat_page = user.PersonalAccessTokenPage(driver, verify=True)
            pat_page.loading_indicator.here_then_gone()
            pat_card = pat_page.get_pat_card_by_name(token_name)

            # Verify that we don't find the PAT card this time since it was deleted
            assert not pat_card
        except Exception:
            # As cleanup, delete the PAT using the api if the test failed for some
            # reason and the PAT was not actually deleted.
            pat_data = osf_api.get_user_pat_data(session, token_id=token_id)
            if pat_data:
                osf_api.delete_personal_access_token(session, token_id=token_id)

    def test_user_settings_delete_PAT_from_list_page(self, driver, session, fake):
        """Delete a Personal Access Token from the User Settings Edit Personal Access
        Token page in OSF. The test uses the OSF api to first create the personal access
        token that will then be deleted using the Front End interface.
        """
        token_name = 'PAT created via api ' + fake.sentence(nb_words=1)
        token_id = osf_api.create_personal_access_token(
            session,
            name=token_name,
            scopes='osf.users.profile_read osf.users.email_read',
        )
        try:
            # Go to the Profile Information page first and use the side navigation bar
            # to then go to the Personal Access Tokens page.
            profile_settings_page = user.ProfileInformationPage(driver)
            profile_settings_page.goto()
            assert user.ProfileInformationPage(driver, verify=True)
            profile_settings_page.side_navigation.personal_access_tokens_link.click()
            pat_page = user.PersonalAccessTokenPage(driver, verify=True)
            pat_page.loading_indicator.here_then_gone()

            # Go through the list of PATs listed on the page to find the one that was
            # just added via the api
            pat_card = pat_page.get_pat_card_by_name(token_name)
            pat_link = pat_card.find_element_by_css_selector('a')
            link_url = pat_link.get_attribute('href')
            link_token_id = link_url.split('tokens/', 1)[1]
            assert link_token_id == token_id

            # Now click the PAT name link to go to the Edit PAT page and verify the
            # data
            pat_link.click()
            edit_page = user.EditPersonalAccessTokenPage(driver, verify=True)
            assert edit_page.token_name_input.get_attribute('value') == token_name
            edit_page.scroll_into_view(edit_page.osf_nodes_full_read_checkbox.element)
            assert not edit_page.osf_nodes_full_read_checkbox.is_selected()
            edit_page.scroll_into_view(
                edit_page.osf_nodes_metadata_read_checkbox.element
            )
            assert not edit_page.osf_nodes_metadata_read_checkbox.is_selected()
            edit_page.scroll_into_view(edit_page.osf_nodes_access_read_checkbox.element)
            assert not edit_page.osf_nodes_access_read_checkbox.is_selected()
            edit_page.scroll_into_view(edit_page.osf_nodes_data_read_checkbox.element)
            assert not edit_page.osf_nodes_data_read_checkbox.is_selected()
            edit_page.scroll_into_view(
                edit_page.osf_users_profile_write_checkbox.element
            )
            assert not edit_page.osf_users_profile_write_checkbox.is_selected()
            edit_page.scroll_into_view(edit_page.osf_full_write_checkbox.element)
            assert not edit_page.osf_full_write_checkbox.is_selected()
            edit_page.scroll_into_view(
                edit_page.osf_nodes_metadata_write_checkbox.element
            )
            assert not edit_page.osf_nodes_metadata_write_checkbox.is_selected()
            edit_page.scroll_into_view(edit_page.osf_full_read_checkbox.element)
            assert not edit_page.osf_full_read_checkbox.is_selected()
            edit_page.scroll_into_view(edit_page.osf_nodes_full_write_checkbox.element)
            assert not edit_page.osf_nodes_full_write_checkbox.is_selected()
            edit_page.scroll_into_view(
                edit_page.osf_nodes_access_write_checkbox.element
            )
            assert not edit_page.osf_nodes_access_write_checkbox.is_selected()
            edit_page.scroll_into_view(edit_page.osf_nodes_data_write_checkbox.element)
            assert not edit_page.osf_nodes_data_write_checkbox.is_selected()
            edit_page.scroll_into_view(edit_page.osf_users_email_read_checkbox.element)
            assert edit_page.osf_users_email_read_checkbox.is_selected()
            edit_page.scroll_into_view(
                edit_page.osf_users_profile_read_checkbox.element
            )
            assert edit_page.osf_users_profile_read_checkbox.is_selected()

            # Click the Back to list of tokens link
            edit_page.back_to_list_of_tokens_link.click()
            assert user.PersonalAccessTokenPage(driver, verify=True)
            pat_page.loading_indicator.here_then_gone()

            # Find the PAT on the list page and click the Delete button on the right
            # side of the card
            pat_card = pat_page.get_pat_card_by_name(token_name)
            assert pat_card
            delete_button = pat_card.find_element_by_css_selector(
                '[data-test-delete-button]'
            )
            delete_button.click()

            # On the Delete Token modal - first click the Cancel button
            delete_modal = pat_page.delete_pat_modal
            assert delete_modal.token_name.text == token_name
            delete_modal.cancel_button.click()

            # Should still be on the PAT list page and the PAT should still be displayed
            pat_page = user.PersonalAccessTokenPage(driver, verify=True)
            pat_page.loading_indicator.here_then_gone()
            pat_card = pat_page.get_pat_card_by_name(token_name)
            assert pat_card

            # Click the Delete button again and this time click the Delete button on the
            # Delete Token Modal
            delete_button = pat_card.find_element_by_css_selector(
                '[data-test-delete-button]'
            )
            delete_button.click()
            delete_modal = pat_page.delete_pat_modal
            assert delete_modal.token_name.text == token_name
            delete_modal.delete_button.click()

            # Should still be on PAT list page
            pat_page = user.PersonalAccessTokenPage(driver, verify=True)
            pat_page.loading_indicator.here_then_gone()
            pat_card = pat_page.get_pat_card_by_name(token_name)

            # Verify that we don't find the PAT card this time since it was deleted
            assert not pat_card
        except Exception:
            # As cleanup, delete the PAT using the api if the test failed for some
            # reason and the PAT was not actually deleted.
            pat_data = osf_api.get_user_pat_data(session, token_id=token_id)
            if pat_data:
                osf_api.delete_personal_access_token(session, token_id=token_id)

    def test_user_settings_edit_PAT(self, driver, session, fake):
        """Edit a Personal Access Token from the User Settings Edit Personal Access
        Token page in OSF. The test uses the OSF api to first create the personal access
        token that will then be edited using the Front End interface. At the end of the
        test the PAT will be deleted using the api as cleanup.
        """
        token_name = 'PAT created via api ' + fake.sentence(nb_words=1)
        token_id = osf_api.create_personal_access_token(
            session, name=token_name, scopes='osf.full_read'
        )
        try:
            pat_page = user.PersonalAccessTokenPage(driver)
            pat_page.goto()
            assert user.PersonalAccessTokenPage(driver, verify=True)
            pat_page.loading_indicator.here_then_gone()

            # Go through the list of PATs listed on the page to find the one that was
            # just added via the api
            pat_card = pat_page.get_pat_card_by_name(token_name)
            pat_link = pat_card.find_element_by_css_selector('a')
            link_url = pat_link.get_attribute('href')
            link_token_id = link_url.split('tokens/', 1)[1]
            assert link_token_id == token_id

            # Now click the PAT name link to go to the Edit PAT page and verify the
            # data
            pat_link.click()
            edit_page = user.EditPersonalAccessTokenPage(driver, verify=True)
            assert edit_page.token_name_input.get_attribute('value') == token_name
            edit_page.scroll_into_view(edit_page.osf_nodes_full_read_checkbox.element)
            assert not edit_page.osf_nodes_full_read_checkbox.is_selected()
            edit_page.scroll_into_view(
                edit_page.osf_nodes_metadata_read_checkbox.element
            )
            assert not edit_page.osf_nodes_metadata_read_checkbox.is_selected()
            edit_page.scroll_into_view(edit_page.osf_nodes_access_read_checkbox.element)
            assert not edit_page.osf_nodes_access_read_checkbox.is_selected()
            edit_page.scroll_into_view(edit_page.osf_nodes_data_read_checkbox.element)
            assert not edit_page.osf_nodes_data_read_checkbox.is_selected()
            edit_page.scroll_into_view(
                edit_page.osf_users_profile_write_checkbox.element
            )
            assert not edit_page.osf_users_profile_write_checkbox.is_selected()
            edit_page.scroll_into_view(edit_page.osf_full_write_checkbox.element)
            assert not edit_page.osf_full_write_checkbox.is_selected()
            edit_page.scroll_into_view(
                edit_page.osf_nodes_metadata_write_checkbox.element
            )
            assert not edit_page.osf_nodes_metadata_write_checkbox.is_selected()
            edit_page.scroll_into_view(edit_page.osf_full_read_checkbox.element)
            assert edit_page.osf_full_read_checkbox.is_selected()
            edit_page.scroll_into_view(edit_page.osf_nodes_full_write_checkbox.element)
            assert not edit_page.osf_nodes_full_write_checkbox.is_selected()
            edit_page.scroll_into_view(
                edit_page.osf_nodes_access_write_checkbox.element
            )
            assert not edit_page.osf_nodes_access_write_checkbox.is_selected()
            edit_page.scroll_into_view(edit_page.osf_nodes_data_write_checkbox.element)
            assert not edit_page.osf_nodes_data_write_checkbox.is_selected()
            edit_page.scroll_into_view(edit_page.osf_users_email_read_checkbox.element)
            assert not edit_page.osf_users_email_read_checkbox.is_selected()
            edit_page.scroll_into_view(
                edit_page.osf_users_profile_read_checkbox.element
            )
            assert not edit_page.osf_users_profile_read_checkbox.is_selected()

            # Make some Edits - change the token name and change permissions from
            # osf.full_read to osf.full_write
            new_token_name = token_name + ' edited'
            edit_page.scroll_into_view(edit_page.token_name_input.element)
            edit_page.token_name_input.clear()
            edit_page.token_name_input.send_keys(new_token_name)
            edit_page.scroll_into_view(edit_page.osf_full_read_checkbox.element)
            edit_page.osf_full_read_checkbox.click()
            edit_page.scroll_into_view(edit_page.osf_full_write_checkbox.element)
            edit_page.osf_full_write_checkbox.click()

            # Click the Save button
            edit_page.scroll_into_view(edit_page.save_button.element)
            edit_page.save_button.click()

            # Should end up back on PAT list page with new token name listed
            pat_page = user.PersonalAccessTokenPage(driver, verify=True)
            pat_page.loading_indicator.here_then_gone()
            pat_card = pat_page.get_pat_card_by_name(new_token_name)
            assert pat_card

            # Now click the PAT name link to go back to the Edit PAT page and verify
            # the data changes
            pat_link = pat_card.find_element_by_css_selector('a')
            pat_link.click()
            edit_page = user.EditPersonalAccessTokenPage(driver, verify=True)
            assert edit_page.token_name_input.get_attribute('value') == new_token_name
            edit_page.scroll_into_view(edit_page.osf_nodes_full_read_checkbox.element)
            assert not edit_page.osf_nodes_full_read_checkbox.is_selected()
            edit_page.scroll_into_view(
                edit_page.osf_nodes_metadata_read_checkbox.element
            )
            assert not edit_page.osf_nodes_metadata_read_checkbox.is_selected()
            edit_page.scroll_into_view(edit_page.osf_nodes_access_read_checkbox.element)
            assert not edit_page.osf_nodes_access_read_checkbox.is_selected()
            edit_page.scroll_into_view(edit_page.osf_nodes_data_read_checkbox.element)
            assert not edit_page.osf_nodes_data_read_checkbox.is_selected()
            edit_page.scroll_into_view(
                edit_page.osf_users_profile_write_checkbox.element
            )
            assert not edit_page.osf_users_profile_write_checkbox.is_selected()
            edit_page.scroll_into_view(edit_page.osf_full_write_checkbox.element)
            assert edit_page.osf_full_write_checkbox.is_selected()
            edit_page.scroll_into_view(
                edit_page.osf_nodes_metadata_write_checkbox.element
            )
            assert not edit_page.osf_nodes_metadata_write_checkbox.is_selected()
            edit_page.scroll_into_view(edit_page.osf_full_read_checkbox.element)
            assert not edit_page.osf_full_read_checkbox.is_selected()
            edit_page.scroll_into_view(edit_page.osf_nodes_full_write_checkbox.element)
            assert not edit_page.osf_nodes_full_write_checkbox.is_selected()
            edit_page.scroll_into_view(
                edit_page.osf_nodes_access_write_checkbox.element
            )
            assert not edit_page.osf_nodes_access_write_checkbox.is_selected()
            edit_page.scroll_into_view(edit_page.osf_nodes_data_write_checkbox.element)
            assert not edit_page.osf_nodes_data_write_checkbox.is_selected()
            edit_page.scroll_into_view(edit_page.osf_users_email_read_checkbox.element)
            assert not edit_page.osf_users_email_read_checkbox.is_selected()
            edit_page.scroll_into_view(
                edit_page.osf_users_profile_read_checkbox.element
            )
            assert not edit_page.osf_users_profile_read_checkbox.is_selected()
        finally:
            # Delete the token using the api as cleanup
            if token_id:
                osf_api.delete_personal_access_token(session, token_id=token_id)
