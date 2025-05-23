# Kismet Website Indexing for NLWeb

This directory contains scripts to automatically index the Kismet website content into NLWeb, making it searchable through the chat interface.

## Primary Indexing Method: RSS Feed

NLWeb has built-in RSS support, making it the simplest way to index content. Kismet provides an RSS feed at:
**https://www.makekismet.com/feed.xml**

### Quick Start - RSS Indexing

```bash
cd NLWeb/code
python -m tools.db_load https://www.makekismet.com/feed.xml makekismet
```

This single command will:
- Fetch the RSS feed
- Parse all items
- Convert to Schema.org format
- Create embeddings
- Store in the vector database

## Alternative Indexing Methods

### Custom Website Indexing Script

The `index-kismet-site.py` script provides more comprehensive indexing by:
- Reading the sitemap.xml
- Fetching content from each page
- Extracting text, metadata, and structured data
- Including FAQ content and PDF metadata

To use:
```bash
cd NLWeb/code
python ../scripts/index-kismet-site.py
```

## Automated Indexing Setup

For daily automatic updates:

1. Deploy the Cloud Run job:
```bash
cd NLWeb/scripts
./deploy-indexing-job.sh
```

2. Follow the output instructions to set up Cloud Scheduler for daily runs at 2 AM.

## What Gets Indexed

### From RSS Feed:
- All items in the feed with full content
- Titles, descriptions, and HTML content
- Categories and publication dates
- Links to original pages

### From Custom Script:
- All pages listed in sitemap.xml
- Page titles, descriptions, and content
- Structured data (JSON-LD) from pages
- FAQ content from the homepage
- PDF documents (metadata only)

## Updating Content

### RSS Feed Updates
1. Edit `frontend/public/feed.xml`
2. Add new `<item>` entries for new content
3. Re-run indexing: `python -m tools.db_load https://www.makekismet.com/feed.xml makekismet`

### Adding New Pages
1. Add page to sitemap.xml
2. Optionally add to RSS feed
3. Run indexing (either method)

## Configuration

- **Site name**: `makekismet` (must match in widget and indexing)
- **RSS feed**: https://www.makekismet.com/feed.xml
- **Sitemap**: https://www.makekismet.com/sitemap.xml
- **Schedule**: Daily at 2 AM (configurable)

## Testing

After indexing, test that content is searchable:

1. Go to https://www.makekismet.com
2. Click the "Chat" button
3. Ask questions like:
   - "What is Kismet?"
   - "How does Direct-to-Guest AI work?"
   - "What channels does Kismet support?"

The NLWeb chat should answer based on your indexed content.

## Troubleshooting

- **RSS feed not loading**: Validate at https://validator.w3.org/feed/
- **Missing content**: Check that content is in RSS feed or sitemap
- **Indexing errors**: View Cloud Run job logs in Google Cloud Console
- **Chat not finding content**: Ensure site parameter "makekismet" matches everywhere
- **Force re-index**: Add `--force-recompute` flag to db_load command 