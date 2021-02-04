from app.jira_metrics import atlassian_auth, config_reader


def test_atlassian_auth():
    """Test if atlassian api auth was sucessful"""
    pass


def test_config_reader():
    """Test config read load"""
    # Given
    config_file = "config_test.yml"

    # When
    result = config_reader(config_file)

    # Then
    assert result['Connection']['Domain'] == "http://tembici.atlassian.net/"

