# Home Assistant IMAP Attachment Component

The `imap_attachment` sensor enables the downloading of attachment files from emails. It extends the official [IMAP Email Content](https://www.home-assistant.io/integrations/imap_email_content/) sensor.


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

For the main variables see the [IMAP Email Content](https://www.home-assistant.io/integrations/imap_email_content/) sensor documentation. The following variables are implemented by this sensor:

#### storage_path (required)

Path to a local PDF file. Default: `/config/attachments`

<hr />

### value_template (optional)

These attributes are available in addition to the [IMAP Email Content](https://www.home-assistant.io/integrations/imap_email_content/) sensor:

- `num_attachments`: Number of email message attachments, excluding the email body
- `attachment_paths`: Full system paths to the latest downloaded attachments

<hr />


## Full Configuration Example

```yaml
# Example configuration.yaml entry
homeassistant:
  allowlist_external_dirs:
    - /config/attachments

sensor:
  - platform: imap_attachment
    name: Utility Bill Email
    server: imap.gmail.com
    port: 993
    username: user@domain.com
    password: hunter2
    senders:
      - noreply@somedomain.com
```

## Implementation Example

Can be used with the [PDF Sensor](https://github.com/emcniece/ha_pdf) to extract data from attachments on emails. In this example, an email from <noreply@somedomain.com> has a PDF attachment with a filename of `utility-bill.pdf`:

```yaml
# Example configuration.yaml entry
homeassistant:
  allowlist_external_dirs:
    - /config/attachments

sensor:
  - platform: imap_attachment
    name: Utility Bill Email
    server: imap.gmail.com
    port: 993
    username: user@domain.com
    password: hunter2
    senders:
      - noreply@somedomain.com

  - platform: pdf
    name: Water Usage Cost
    file_path: /config/attachments/utility-bill.pdf
    unit_of_measurement: $
    regex_search: 'Water Consumption Charge\s+([\d.]+)\s+x\s+\$\s+([\d.]+)\s+([\d.]+)\s-+'
    regex_match_index: 3
```
