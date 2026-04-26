from datetime import timedelta

DOMAIN = "food_box_tracker"

CONF_PROVIDER = "provider"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"

PROVIDER_GOUSTO = "gousto"
PROVIDER_GREEN_CHEF = "green_chef"

PROVIDERS = {
    PROVIDER_GOUSTO: "Gousto",
    PROVIDER_GREEN_CHEF: "Green Chef",
}

UPDATE_INTERVAL = timedelta(hours=6)
