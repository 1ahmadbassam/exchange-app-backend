from typing import Optional

from rss_parser.models import XMLBaseModel, pydantic
from rss_parser.models.rss.channel import RequiredChannelElementsMixin, OptionalChannelElementsMixin
from rss_parser.models.rss.item import RequiredItemElementsMixin, OptionalItemElementsMixin
from rss_parser.models.types.only_list import OnlyList
from rss_parser.models.types.tag import Tag


class Media(XMLBaseModel):
    url: Tag[str] = None
    medium: Tag[str] = None
    type: Tag[str] = None


class Item(RequiredItemElementsMixin, OptionalItemElementsMixin, XMLBaseModel):
    media: Tag[Media] = pydantic.Field(alias="media:content", default=[])


class Channel(RequiredChannelElementsMixin, OptionalChannelElementsMixin, XMLBaseModel):
    items: Optional[OnlyList[Tag[Item]]] = pydantic.Field(alias="item", default=[])


class RSS(XMLBaseModel):
    version: Optional[Tag[str]] = pydantic.Field(alias="@version")
    channel: Tag[Channel]
