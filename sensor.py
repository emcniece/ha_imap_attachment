import os
import logging
import email
import imaplib
import datetime
from collections import deque

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.typing import HomeAssistantType
from homeassistant.helpers.config_validation import PLATFORM_SCHEMA
from homeassistant.const import (
    ATTR_DATE,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_USERNAME,
    CONTENT_TYPE_TEXT_PLAIN,
)
import voluptuous as vol
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(name)

CONF_SERVER = "server"
CONF_SENDERS = "senders"
CONF_FOLDER = "folder"
CONF_STORAGE_PATH = "storage_path"
CONF_MARK_AS_READ = "mark_as_read"

ATTR_FROM = "from"
ATTR_BODY = "body"
ATTR_SUBJECT = "subject"
ATTR_NUM_ATTACHMENTS = "num_attachments"
ATTR_ATTACHMENT_PATHS = "attachment_paths"

DEFAULT_PORT = 993
DEFAULT_FOLDER = "INBOX"
DEFAULT_STORAGE_PATH = "/config/attachments"
DEFAULT_MARK_AS_READ = True

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_NAME): cv.string,
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Required(CONF_SERVER): cv.string,
        vol.Required(CONF_SENDERS): vol.All(cv.ensure_list, [cv.string]),
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
        vol.Optional(CONF_FOLDER, default=DEFAULT_FOLDER): cv.string,
        vol.Optional(CONF_STORAGE_PATH, default=DEFAULT_STORAGE_PATH): cv.string,
        vol.Optional(CONF_MARK_AS_READ, default=DEFAULT_MARK_AS_READ): cv.boolean,
    }
)

async def async_setup_platform(hass: HomeAssistantType, config, async_add_entities, discovery_info=None):
    """Set up the Email Sensor platform."""
    username = config[CONF_USERNAME]
    password = config[CONF_PASSWORD]
    server = config[CONF_SERVER]
    port = config[CONF_PORT]
    folder = config[CONF_FOLDER]
    senders = config[CONF_SENDERS]
    storage_path = config[CONF_STORAGE_PATH]
    mark_as_read = config[CONF_MARK_AS_READ]
    name = config.get(CONF_NAME, "Email Sensor")

    # Ensure storage_path exists
    os.makedirs(storage_path, exist_ok=True)

    email_reader = EmailReader(username, password, server, port, folder, storage_path, mark_as_read)
    sensor = EmailContentSensor(hass, email_reader, name, senders, storage_path)

    if email_reader.connect():
        async_add_entities([sensor], True)
    else:
        _LOGGER.error("Failed to connect to email server %s", server)

class EmailReader:
    """A class to read emails from an IMAP server."""

    def __init__(self, username, password, server, port, folder, storage_path, mark_as_read):
        self._username = username
        self._password = password
        self._server = server
        self._port = port
        self._folder = folder
        self._storage_path = storage_path
        self._mark_as_read = mark_as_read
        self._unread_ids = deque()
        self.connection = None

    def connect(self):
        """Login to the IMAP server."""
        try:
            self.connection = imaplib.IMAP4_SSL(self._server, self._port)
            self.connection.login(self._username, self._password)
            return True
        except imaplib.IMAP4.error as e:
            _LOGGER.error("Failed to login to %s: %s", self._server, e)
            return False

    def read_next(self):
        """Read the next unread email and optionally mark it as read."""
        try:
            # Open the folder in read/write mode
            self.connection.select(self._folder, readonly=not self._mark_as_read)

            if not self._unread_ids:
                # Search for unread emails
                _, data = self.connection.uid("search", None, "UNSEEN")
                self._unread_ids = deque(data[0].split())

            if self._unread_ids:
                message_uid = self._unread_ids.popleft()
                _, message_data = self.connection.uid("fetch", message_uid, "(RFC822)")
                if message_data and message_data[0]:
                    # Mark the message as read if the option is enabled
                    if self._mark_as_read:
                        self.connection.uid("store", message_uid, "+FLAGS", "(\\Seen)")
                    return email.message_from_bytes(message_data[0][1])

        except imaplib.IMAP4.error as e:
            _LOGGER.warning("IMAP error: %s", e)
            self.connect()

        return None

class EmailContentSensor(SensorEntity):
    """Representation of an email sensor."""

    def __init__(self, hass, email_reader, name, allowed_senders, storage_path):
        self.hass = hass
        self._email_reader = email_reader
        self._name = name
        self._allowed_senders = [sender.upper() for sender in allowed_senders]
        self._storage_path = storage_path
        self._message = None
        self._attributes = {}

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the subject of the most recent email."""
        return self._message

    @property
    def extra_state_attributes(self):
        """Return the sensor attributes."""
        return self._attributes

    async def async_update(self):
        """Fetch new data for the sensor."""
        email_message = await self.hass.async_add_executor_job(self._email_reader.read_next)

        if email_message:
            sender = EmailContentSensor.get_msg_sender(email_message)
            if sender.upper() in self._allowed_senders:
                self._message = EmailContentSensor.get_msg_subject(email_message)
                attachments = await EmailContentSensor.get_msg_attachments(email_message, self._storage_path, self.hass)

                self._attributes = {
                    ATTR_FROM: sender,
                    ATTR_SUBJECT: self._message,
                    ATTR_DATE: email_message["Date"],
                    ATTR_BODY: EmailContentSensor.get_msg_text(email_message),
                    ATTR_NUM_ATTACHMENTS: len(attachments),
                    ATTR_ATTACHMENT_PATHS: attachments,
                }

                # Fire a custom event when an email is processed
                self.hass.bus.fire(
                    "imap_attachment",
                    {
                        "from": sender,
                        "subject": self._message,
                        "date": email_message["Date"],
                        "body": self._attributes[ATTR_BODY],
                        "attachments": attachments,
                    },
                )
                _LOGGER.info("Fired imap_attachment event with attachments: %s", attachments)

    @staticmethod
    def get_msg_sender(email_message):
        """Get the sender's email address."""
        return email.utils.parseaddr(email_message["From"])[1]

    @staticmethod
    def get_msg_subject(email_message):
        """Get the email subject."""
        return str(email.header.make_header(email.header.decode_header(email_message["Subject"])))

    @staticmethod
    def get_msg_text(email_message):
        """Extract plain text from the email."""
        for part in email_message.walk():
            if part.get_content_type() == CONTENT_TYPE_TEXT_PLAIN:
                return part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8")
        return ""

    @staticmethod
    async def get_msg_attachments(email_message, storage_path, hass):
        """Save attachments asynchronously and return their paths."""
        attachments = []

        def save_attachment(part, filepath):
            """Blocking function to save the attachment."""
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "wb") as file:
                file.write(part.get_payload(decode=True))
            return filepath

        for part in email_message.walk():
            if part.get("Content-Disposition") and "attachment" in part.get("Content-Disposition"):
                filename = part.get_filename()
                if filename:
                    filepath = os.path.join(storage_path, filename)
                    saved_path = await hass.async_add_executor_job(save_attachment, part, filepath)
                    attachments.append(saved_path)

        return attachments
