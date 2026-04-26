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

# Fired by each coordinator after a successful data refresh so combined
# entities can update without being tied to a single coordinator.
SIGNAL_COORDINATOR_UPDATED = f"{DOMAIN}_coordinator_updated"

# Order statuses that mean "you still need to choose your recipes".
# These are based on known unofficial API values and may need adjusting.
GOUSTO_NEEDS_SELECTION_STATUSES: frozenset[str] = frozenset(
    {"pending", "menu_open", "requires_action"}
)
GREEN_CHEF_NEEDS_SELECTION_STATUSES: frozenset[str] = frozenset(
    {"pending", "open", "unconfirmed"}
)
