# Food Box Tracker

A Home Assistant custom integration for tracking food box deliveries. Currently supports **Gousto** and **Green Chef** (UK), with an extensible provider architecture for adding more services in the future.

## Features

Each configured account exposes the following sensors:

| Sensor | Description |
|--------|-------------|
| **Next Delivery Date** | Date of your next scheduled delivery |
| **Order Status** | Current status of your next order (e.g. `confirmed`, `dispatched`) |
| **Recipe Count** | Number of recipes in your next box |
| **Delivery Slot** | Your allocated delivery time window |
| **Box Type** | The box/plan type you are subscribed to |

The `Recipe Count` sensor also exposes a `recipes` attribute listing the individual recipe names, and `Order Status` exposes `order_number`, `price`, and `upcoming_delivery_count`.

## Installation

### Via HACS (recommended)

1. Open HACS in your Home Assistant instance.
2. Go to **Integrations** → **Custom repositories**.
3. Add `https://github.com/harrytouche/food-box-tracker` with category **Integration**.
4. Search for **Food Box Tracker** and install it.
5. Restart Home Assistant.

### Manual

1. Copy the `custom_components/food_box_tracker` folder into your HA `config/custom_components/` directory.
2. Restart Home Assistant.

## Configuration

1. Go to **Settings → Devices & Services → Add Integration**.
2. Search for **Food Box Tracker**.
3. Select your provider (Gousto or Green Chef) and enter your account email and password.
4. Repeat for each account/provider you want to track.

## Update Interval

Data is refreshed every **6 hours** by default. You can trigger a manual refresh from the integration's device page.

## Supported Providers

| Provider | Status |
|----------|--------|
| Gousto (UK) | Supported |
| Green Chef (UK) | Supported |

> **Note:** These integrations use unofficial/undocumented APIs. They may break if the providers update their backend. Please open an issue if you encounter problems.

## Adding a New Provider

1. Create `custom_components/food_box_tracker/providers/<name>.py` implementing the `FoodBoxProvider` abstract class from `providers/base.py`.
2. Register the new provider in `const.py` (`PROVIDERS` dict) and `coordinator.py`.
3. Add config flow labels to `strings.json` and `translations/en.json`.

## Troubleshooting

Enable debug logging in `configuration.yaml`:

```yaml
logger:
  default: warning
  logs:
    custom_components.food_box_tracker: debug
```
