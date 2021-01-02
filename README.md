# Home Assistant IMAP Attachment Component

The `imap_attachment` sensor enables the downloading of attachment files from emails.


## Installation

Clone this repo into the `custom_components` directory:

```sh
cd [HA_HOME]/custom_components
git clone https://github.com/emcniece/ha_imap_attachment.git
```

## Configuration

Home Assistant must first be allowed to access the directory with the target PDF file. Add the [allowlist_external_dirs](https://www.home-assistant.io/docs/configuration/basic/#allowlist_external_dirs) to `configuration.yaml`. In this example, the PDF exists at `/config/my.pdf`:

```yaml
homeassistant:
  allowlist_external_dirs:
    - /config/attachments
```

Next add the sensor definition:

```yaml
sensor:
  - platform: imap_attachment
    name: IMAP Attachments
    storage_path: /config/attachments
```

By default this configuration will extract all text content found in the first page of the PDF.

### Configuration Variables

#### storage_path (required)

Path to a local PDF file

<hr />


## Full Configuration Example



```yaml
# Example configuration.yaml entry
homeassistant:
  allowlist_external_dirs:
    - /config/attachments

sensor:
  - platform: pdf
    name: Water Usage Volume
    storage_path: /config/attachments
  
```
