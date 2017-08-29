from blocks.login import Login
from blocks.forks import Forks
from blocks.nodes import Nodes
from selenium import webdriver
from blocks.contributors import Contributors

desired_cap = {'browser': 'Chrome', 'browser_version': '59.0', 'os': 'OS X', 'os_version': 'Sierra', 'resolution': '1920x1080'}
driver = webdriver.Remote(
command_executor='http://osfselenium1:9asHrZGoyk7Tesx9agX5@hub.browserstack.com:80/wd/hub',
desired_capabilities=desired_cap)

def test_forks():
    l = Login()
    #f = Forks()
    p = Nodes()
    c= Contributors()
    l.staging_login(driver)
    project_id = p.create_project(driver)
    c.search_contributors(driver)
    #assert driver.find_element_by_id("nodeTitleEditable")
    #p.delete_node(driver, fork_id + 'settings/')
    #p.delete_node(driver, project_id + 'settings/')
    driver.quit()
