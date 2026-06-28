SCRAPER_REGISTRY = {
    "atacadao": "scrapers.atacadao.scraper.AtacadaoScraper",
    "carrefour": "scrapers.carrefour.scraper.CarrefourScraper",
    "mix_mateus": "scrapers.mix_mateus.scraper.MixMateusScraper"
}


def get_scraper(
    market
):

    try:
        scraper_path = SCRAPER_REGISTRY[market]
    except KeyError as error:
        available = ", ".join(sorted(SCRAPER_REGISTRY))
        raise ValueError(
            f"Unknown market '{market}'. Available markets: {available}"
        ) from error

    module_path, class_name = scraper_path.rsplit(".", 1)
    module = __import__(
        module_path,
        fromlist=[class_name]
    )
    scraper_class = getattr(module, class_name)

    return scraper_class()
