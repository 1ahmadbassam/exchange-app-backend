import datetime

from sqlalchemy.orm import Mapped, mapped_column

from init import db, ma


class News(db.Model):
    __tablename__ = 'news'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    headline: Mapped[str] = mapped_column(db.Text, nullable=False)
    content: Mapped[str] = mapped_column(db.Text, nullable=False)
    source: Mapped[str] = mapped_column(db.Text, nullable=False)
    impact: Mapped[int] = mapped_column(nullable=False)
    impact_summary: Mapped[str] = mapped_column(db.Text, nullable=False)
    confidence: Mapped[float] = mapped_column(nullable=False)
    timestamp: Mapped[datetime.datetime] = mapped_column(nullable=False)
    url: Mapped[str] = mapped_column(db.Text, nullable=False)
    image: Mapped[str] = mapped_column(db.Text, nullable=False)

    def __init__(self, headline, content, source, impact, impact_summary, confidence, timestamp, url, image):
        super(News, self).__init__(headline=headline,
                                   content=content,
                                   impact=impact,
                                   source=source,
                                   impact_summary=impact_summary,
                                   confidence=confidence,
                                   timestamp=timestamp,
                                   url=url,
                                   image=image)


class NewsSchema(ma.Schema):
    class Meta:
        fields = (
        "id", "headline", "content", "source", "impact", "impact_summary", "confidence", "timestamp", "url", "image")
        model = News
