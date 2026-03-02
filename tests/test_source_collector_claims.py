from bs4 import BeautifulSoup

from notebook_lm.source_collector import SourceCollector


def test_extract_key_claims_uses_title_preview_and_article_text():
    collector = SourceCollector()
    html = """
    <html>
      <head>
        <title>US and Israel launch strikes on Iran</title>
        <meta name="description" content="US and Israeli forces launched coordinated strikes on Iranian military facilities." />
      </head>
      <body>
        <article>
          <p>Iran responded with missile and drone attacks aimed at Israel and US positions in the Gulf.</p>
          <p>Officials said the overnight operation targeted nuclear and military infrastructure.</p>
        </article>
      </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")

    claims = collector._extract_key_claims(
        "US and Israel launch strikes on Iran",
        "US and Israeli forces launched coordinated strikes on Iranian military facilities.",
        soup,
        "US and Israel launch strikes on Iran 2026-02-28",
    )

    assert claims
    assert any("strikes on iran" in claim.lower() for claim in claims)
    assert any("missile and drone" in claim.lower() for claim in claims)


def test_extract_key_claims_falls_back_to_title_when_article_text_missing():
    collector = SourceCollector()
    soup = BeautifulSoup("<html><body></body></html>", "html.parser")

    claims = collector._extract_key_claims(
        "US and Israel launch strikes on Iran",
        "Preview unavailable from direct scrape. Derived title: us and israel launch strikes on iran",
        soup,
        "US and Israel launch strikes on Iran 2026-02-28",
    )

    assert claims == ["US and Israel launch strikes on Iran"]
