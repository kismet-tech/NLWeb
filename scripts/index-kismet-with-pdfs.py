#!/usr/bin/env python3
"""
Enhanced script to index ALL Kismet content including PDF text extraction.
Combines sitemap URLs + RSS feed items + local PDF resources for complete coverage.
"""

import asyncio
import aiohttp
import json
import os
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, List, Any, Set
from bs4 import BeautifulSoup
import re
import feedparser
import PyPDF2
from pathlib import Path

# Add the code directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'code'))

# Import db_load functionality
from tools.db_load import loadJsonToDB, delete_site_from_database

SITE_NAME = "makekismet"
SITEMAP_URL = "https://www.makekismet.com/sitemap.xml"
RSS_FEED_URL = "https://www.makekismet.com/feed.xml"
SITE_BASE_URL = "https://www.makekismet.com"

# Path to local resources (relative to script location)
RESOURCES_PATH = "../../frontend/public/resources"

def enhance_keywords_for_faq(question_name: str, answer_text: str) -> List[str]:
    """Add semantic keywords based on FAQ content to improve casual language matching."""
    keywords = []
    
    # Normalize text for matching
    question_lower = question_name.lower()
    answer_lower = answer_text.lower()
    combined_text = f"{question_lower} {answer_lower}"
    
    # Pricing/Cost related keywords
    if any(term in combined_text for term in ['roi', 'cost', 'price', 'pricing', 'payment', 'roas', 'pay-as-you-grow']):
        keywords.extend([
            'pricing', 'cost', 'payment model', 'price', 'pricing model', 
            'cost structure', 'payment terms', 'expensive', 'cheap', 'affordable',
            'how much', 'what does it cost', 'is it expensive', 'pricing structure',
            'budget', 'investment', 'roi', 'return on investment', 'value'
        ])
    
    # Setup/Installation related keywords  
    if any(term in combined_text for term in ['setup', 'install', 'launch', 'integration', 'deploy', 'implement']):
        keywords.extend([
            'installation', 'setup', 'implementation', 'getting started',
            'install', 'deploy', 'integrate', 'setup time', 'hard to setup',
            'difficult to install', 'easy to setup', 'quick setup', 'fast launch',
            'how long', 'timeline', 'onboarding'
        ])
    
    # PMS/Technical integration keywords
    if any(term in combined_text for term in ['pms', 'property management', 'mews', 'cloudbeds', 'stayntouch']):
        keywords.extend([
            'property management system', 'hotel software', 'PMS integration',
            'booking engine', 'CRM', 'system integration', 'API', 'technical'
        ])
    
    # Features/Functionality keywords
    if any(term in combined_text for term in ['ai', 'direct-to-guest', 'personalize', 'channel', 'feature', 'dashboard', 'email', 'marketing']):
        keywords.extend([
            'features', 'capabilities', 'functionality', 'what does it do',
            'how does it work', 'benefits', 'advantages', 'tools', 'platform'
        ])
    
    # Staff/Management keywords
    if any(term in combined_text for term in ['staff', 'time', 'manage', 'team']):
        keywords.extend([
            'staff time', 'management', 'team effort', 'workload', 'maintenance',
            'how much work', 'time consuming', 'easy to manage'
        ])
    
    return list(set(keywords))  # Remove duplicates

def enhance_keywords_for_content(title: str, description: str, content: str) -> List[str]:
    """Generate enhanced keywords for general content (non-FAQ)."""
    keywords = []
    
    # Combine all text for analysis
    combined_text = f"{title.lower()} {description.lower()} {content.lower()}"
    
    # Feature-specific keywords
    if any(term in combined_text for term in ['email', 'dashboard', 'outreach', 'personalized']):
        keywords.extend([
            'email marketing', 'guest outreach', 'personalized communication',
            'email campaigns', 'guest engagement', 'marketing automation'
        ])
    
    if any(term in combined_text for term in ['marketing', 'lists', 'database', 'segmentation']):
        keywords.extend([
            'marketing lists', 'guest database', 'contact management',
            'segmentation', 'guest data', 'marketing contacts'
        ])
    
    if any(term in combined_text for term in ['demo', 'video', 'demonstration']):
        keywords.extend([
            'product demo', 'video demonstration', 'platform walkthrough',
            'how it works', 'see in action', 'live demo'
        ])
    
    # Industry insights and research keywords
    if any(term in combined_text for term in ['ota', 'booking', 'direct', 'channel', 'research', 'study', 'data']):
        keywords.extend([
            'industry research', 'booking behavior', 'ota vs direct',
            'guest behavior', 'booking patterns', 'industry insights',
            'hotel research', 'booking data', 'guest preferences'
        ])
    
    # OTA and direct booking keywords
    if any(term in combined_text for term in ['ota', 'expedia', 'booking.com', 'direct booking']):
        keywords.extend([
            'ota competition', 'direct booking strategy', 'online travel agency',
            'booking.com alternative', 'expedia alternative', 'direct channel',
            'ota leakage', 'commission free booking'
        ])
    
    # General hotel/AI keywords
    if any(term in combined_text for term in ['hotel', 'guest', 'booking', 'ai', 'direct']):
        keywords.extend([
            'hotel technology', 'guest experience', 'direct booking',
            'hotel AI', 'hospitality technology', 'hotel software'
        ])
    
    return list(set(keywords))

def extract_pdf_text(pdf_path: str) -> str:
    """Extract text content from a PDF file."""
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text += page.extract_text() + "\n"
            
            return text.strip()
    except Exception as e:
        print(f"Error extracting text from {pdf_path}: {str(e)}")
        return ""

def scan_local_resources() -> List[Dict[str, Any]]:
    """Scan local resources directory for PDFs and other content."""
    resources = []
    
    # Check if we're running in Cloud Run (no local files available)
    is_cloud_run = os.environ.get('K_SERVICE') is not None
    
    if is_cloud_run:
        # In Cloud Run, create documents for known PDFs without local access
        pdf_resources = [
            {
                "filename": "Kismet_teaser_v2.1_20250523.pdf",
                "title": "Kismet Direct-to-Guest AI Product Teaser",
                "description": "Comprehensive product teaser showcasing Kismet's Direct-to-Guest AI platform capabilities, features, and benefits for hotels.",
                "keywords": ["direct-to-guest", "ai platform", "hotel technology", "product overview", "features", "benefits"],
                "document_type": "product_teaser"
            },
            {
                "filename": "MEMO_ 4 in 5 OTA Bookers Visited a Direct Channel—Why Didn't They Book There?.pdf",
                "title": "Industry Research: 4 in 5 OTA Bookers Visited a Direct Channel—Why Didn't They Book There?",
                "description": "Industry research memo analyzing why guests who visit hotel direct channels still book through OTAs, and strategies to capture direct bookings.",
                "keywords": ["ota research", "direct booking", "guest behavior", "industry research", "booking patterns"],
                "document_type": "research_memo"
            },
            {
                "filename": "Kismet Unveils Kismet Connect for Instagram.pdf",
                "title": "Kismet Connect for Instagram Announcement",
                "description": "Press release announcing Kismet Connect for Instagram, enabling direct hotel bookings through Instagram.",
                "keywords": ["instagram", "social media booking", "kismet connect", "announcement", "press release"],
                "document_type": "press_release"
            }
        ]
        
        for pdf in pdf_resources:
            doc = {
                "url": f"https://www.makekismet.com/resources/{pdf['filename']}",
                "name": pdf["title"],
                "@type": "DigitalDocument",
                "site": SITE_NAME,
                "description": pdf["description"],
                "text": f"This is a PDF document: {pdf['description']}. For full content, please download from the URL.",
                "keywords": enhance_keywords_for_content(pdf["title"], pdf["description"], " ".join(pdf["keywords"])),
                "source": "pdf_resource",
                "document_type": pdf["document_type"]
            }
            resources.append(doc)
        
        return resources
    
    # Original local file scanning code for development
    # Get the absolute path to resources directory
    script_dir = Path(__file__).parent
    
    # Try multiple possible paths for resources
    possible_paths = [
        script_dir / RESOURCES_PATH,  # Local development path
        script_dir / "../resources",   # Docker container path
        Path("/app/resources"),        # Absolute Docker path
    ]
    
    resources_dir = None
    for path in possible_paths:
        if path.exists():
            resources_dir = path
            break
    
    if not resources_dir:
        print(f"Resources directory not found. Tried paths: {[str(p) for p in possible_paths]}")
        return resources
    
    print(f"Scanning resources directory: {resources_dir}")
    
    # Scan for PDF files
    for pdf_file in resources_dir.glob("*.pdf"):
        print(f"Found PDF: {pdf_file.name}")
        
        # Extract text from PDF
        pdf_text = extract_pdf_text(str(pdf_file))
        
        # Create document based on filename
        if "memo" in pdf_file.name.lower() and "ota" in pdf_file.name.lower():
            # This is the OTA research memo
            doc = {
                "url": f"https://www.makekismet.com/resources/{pdf_file.name}",
                "name": "Industry Research: 4 in 5 OTA Bookers Visited a Direct Channel—Why Didn't They Book There?",
                "@type": "ResearchDocument",
                "site": SITE_NAME,
                "description": "Industry research memo analyzing why guests who visit hotel direct channels still book through OTAs, and strategies to capture direct bookings.",
                "text": pdf_text[:8000],  # Limit text length but allow more for research content
                "keywords": enhance_keywords_for_content(
                    "OTA Research Memo",
                    "Industry research on direct booking vs OTA behavior",
                    f"ota booking direct channel research guest behavior {pdf_text[:1000]}"
                ),
                "source": "pdf_resource",
                "document_type": "research_memo"
            }
        elif "teaser" in pdf_file.name.lower():
            # This is the product teaser
            doc = {
                "url": f"https://www.makekismet.com/resources/{pdf_file.name}",
                "name": "Kismet Direct-to-Guest AI Product Teaser",
                "@type": "PresentationDigitalDocument",
                "site": SITE_NAME,
                "description": "Comprehensive product teaser showcasing Kismet's Direct-to-Guest AI platform capabilities, features, and benefits for hotels.",
                "text": pdf_text[:8000],
                "keywords": enhance_keywords_for_content(
                    "Kismet Product Teaser",
                    "Direct-to-Guest AI platform overview",
                    f"direct-to-guest ai hotel platform features {pdf_text[:1000]}"
                ),
                "source": "pdf_resource",
                "document_type": "product_teaser"
            }
        else:
            # Generic PDF document
            doc = {
                "url": f"https://www.makekismet.com/resources/{pdf_file.name}",
                "name": f"Kismet Resource: {pdf_file.stem}",
                "@type": "DigitalDocument",
                "site": SITE_NAME,
                "description": f"Kismet resource document: {pdf_file.stem}",
                "text": pdf_text[:8000],
                "keywords": enhance_keywords_for_content(
                    pdf_file.stem,
                    "Kismet resource document",
                    pdf_text[:1000]
                ),
                "source": "pdf_resource",
                "document_type": "resource"
            }
        
        resources.append(doc)
    
    return resources

def get_page_specific_faqs(url: str) -> List[Dict[str, Any]]:
    """Get page-specific FAQs based on URL since they're added client-side."""
    faqs = []
    
    if url.endswith('/sales') or '/sales#' in url:
        # Sales page FAQs
        sales_faqs = [
            {
                "question": "How does Kismet help my sales team spend less time on unqualified leads?",
                "answer": "Kismet automatically qualifies leads using your hotel's past conversion data and real-time availability, ensuring your sales team only spends time on prospects with genuine booking intent and budget fit."
            },
            {
                "question": "What types of leads does Kismet generate - are they mainly transient guests or group/corporate bookings?",
                "answer": "Kismet specializes in leisure and social group segments—particularly smaller social groups that traditional sales processes often miss. We help you capture and nurture these high-value prospects with minimal manual effort from your sales team."
            },
            {
                "question": "How does Kismet integrate with our existing CRM and sales processes?",
                "answer": "Kismet integrates seamlessly with Tripleseat and Event Temple (in beta). For smaller properties, Kismet's built-in CRM capabilities are robust enough to serve as your primary sales management system."
            },
            {
                "question": "Can Kismet help with group RFPs and meeting planner outreach?",
                "answer": "Yes, Kismet streamlines RFP processing from both form submissions and natural language inquiries—whether through chat, email, or social media—and automatically drafts personalized initial responses for your review."
            },
            {
                "question": "How much time will my sales team save per week using Kismet?",
                "answer": "Hotels using Kismet typically cut sales busywork in half, saving an average of 10 hours per week. This lets your team focus on closing deals instead of chasing unqualified leads."
            },
            {
                "question": "Does Kismet provide sales attribution - can we track which channels generate the best converting leads?",
                "answer": "Attribution is core to what we do. Social groups are notoriously difficult to track due to long lead times and informal booking processes. Kismet shows you exactly which Instagram posts, ads, or touchpoints drive leads—and whether they actually convert to bookings."
            },
            {
                "question": "How does Kismet handle lead scoring and qualification criteria?",
                "answer": "Our proprietary lead scoring model analyzes your hotel's historical sales data combined with real-time contribution and displacement analysis, ensuring you prioritize prospects most likely to book and generate incremental revenue."
            },
            {
                "question": "Can our sales team customize offers and pricing for leads generated by Kismet?",
                "answer": "Absolutely. Kismet gives you the control on pricing and packaging as well as which types of leads to offer instant-book to and which will require personal touch."
            },
            {
                "question": "How do I make sure AI can find my hotel?",
                "answer": "To ensure AI discovery, hotels need to integrate Natural Language Web (NLWeb) and Model Context Protocol (MCP) best practices. Specifically, this means: 1) Maintain updated structured data (Schema.org markup) on their website, 2) Keep RSS feeds current with fresh content, 3) Allow AI crawlers like GPTBot and PerplexityBot access via robots.txt, 4) Publish regular content about amenities, local attractions, and unique offerings, and 5) Ensure their booking engine and website have clear, semantic HTML markup that AI can understand."
            },
            {
                "question": "How does Kismet increase direct bookings?",
                "answer": "Kismet increases direct bookings by offering guests a private booking channel with offers just for them. Specifically, this involves: 1) Identifying guests early in their search journey across social media, web, and email, 2) Creating personalized private-rate offers that aren't available on OTAs, 3) Using AI to match guests with relevant packages and experiences, 4) Converting social media interest into attributable bookings through natural language conversations, and 5) Building owned marketing audiences that reduce dependence on third-party channels while increasing repeat bookings."
            },
            {
                "question": "Does Kismet replace my booking engine?",
                "answer": "No, Kismet doesn't replace your booking engine, PMS, or CRS. Kismet is a lightweight AI layer that integrates with your existing systems through standard APIs. It enhances your current tech stack by adding conversational AI capabilities and intelligent guest matching, while all bookings flow through your existing booking engine and reservations appear in your current PMS. No software gets ripped out - Kismet just makes your existing systems smarter."
            }
        ]
        for i, faq in enumerate(sales_faqs):
            faqs.append({
                "url": f"{url}#sales-faq-{i+1}",
                "name": f"Sales FAQ: {faq['question']}",
                "@type": "Question",
                "site": SITE_NAME,
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": faq['answer']
                },
                "keywords": enhance_keywords_for_faq(faq['question'], faq['answer']),
                "description": f"Sales FAQ about {faq['question'].lower()}",
                "source": "sales_page_faq"
            })
    
    elif url.endswith('/nlweb') or '/nlweb#' in url:
        # NLWeb page FAQs (17 total)
        nlweb_faqs = [
            {
                "question": "What is NLWeb?",
                "answer": "Natural Language Web (NLWeb) is an open protocol developed by Microsoft that makes websites discoverable and understandable by AI assistants. It allows websites to add conversational interfaces and expose their content to AI systems like ChatGPT, Claude, and Perplexity. Think of it as making your hotel 'AI-readable' - when guests ask AI for hotel recommendations, NLWeb ensures your property appears with accurate, compelling information."
            },
            {
                "question": "How does Kismet use NLWeb for hotels?",
                "answer": "Kismet implements NLWeb to ensure your hotel is discoverable by AI assistants. We structure your hotel's content - from room descriptions to amenities and local attractions - in a way that AI can understand and recommend. When potential guests ask AI platforms for hotel suggestions, Kismet's NLWeb implementation ensures your property is presented accurately with real-time availability and personalized recommendations."
            },
            {
                "question": "Which AI platforms can discover my hotel through NLWeb?",
                "answer": "NLWeb works with all major AI platforms including ChatGPT, Claude, Perplexity, Google's AI assistants, and emerging platforms. Because NLWeb is built on open standards and integrates with Model Context Protocol (MCP), your hotel becomes discoverable by current AI systems and future platforms as they emerge."
            },
            {
                "question": "How is NLWeb different from traditional SEO?",
                "answer": "Traditional SEO optimizes for search engines using keywords, backlinks, and meta tags to rank in search results. NLWeb optimizes for AI understanding using semantic data, structured content, and natural language interfaces. While SEO helps people find your website through Google, NLWeb helps AI assistants understand and recommend your hotel in conversational contexts when guests ask questions like 'Where should I stay for a romantic weekend in Napa Valley?'"
            },
            {
                "question": "Do I need to rebuild my website to use NLWeb?",
                "answer": "No, you don't need to rebuild your website. NLWeb works with your existing site by leveraging structured data you may already have (like Schema.org markup) and adding a lightweight layer that makes your content AI-readable. Kismet handles the technical implementation, ensuring your current website design and user experience remain unchanged while becoming discoverable by AI."
            },
            {
                "question": "How quickly will AI start finding my hotel after implementing NLWeb?",
                "answer": "Most hotels see their content indexed by AI platforms within 48-72 hours of NLWeb implementation. You'll start seeing AI-driven traffic and inquiries within the first week. The full benefits - including improved AI recommendations and higher visibility in conversational queries - typically materialize within 30 days as AI systems learn and index your structured content."
            },
            {
                "question": "What kind of hotel information does NLWeb make available to AI?",
                "answer": "NLWeb structures all your hotel's key information for AI consumption: room types and amenities, real-time availability and pricing, location and nearby attractions, dining options and spa services, special packages and promotions, guest policies, and unique selling points. You maintain full control over what information is shared, ensuring AI presents your hotel accurately while protecting sensitive data."
            },
            {
                "question": "Can NLWeb help with voice search and AI assistants like Alexa?",
                "answer": "Yes, NLWeb is designed to work with all forms of AI interaction, including voice assistants. As more travelers use voice search to plan trips, NLWeb ensures your hotel is discoverable through natural language queries across all AI platforms, whether text-based like ChatGPT or voice-based like Alexa and Google Assistant."
            },
            {
                "question": "How does NLWeb protect my hotel's data and pricing?",
                "answer": "NLWeb includes built-in access controls that let you decide what information AI can access. You can share public information like amenities and location while keeping sensitive data like revenue metrics private. Pricing can be shown as ranges or dynamically updated based on your revenue management rules, maintaining rate parity while enabling AI discovery."
            },
            {
                "question": "What's the ROI of implementing NLWeb for hotels?",
                "answer": "Hotels implementing NLWeb saw a double-digit contribution from AI traffic within weeks of implementation. As AI adoption grows - with over 180 million ChatGPT users alone - being discoverable by AI becomes essential. Early adopters gain competitive advantage by appearing in AI recommendations while competitors remain invisible to these platforms."
            },
            {
                "question": "Can't my hotel just implement the open source NLWeb protocol ourselves?",
                "answer": "While NLWeb is open source, implementing it effectively for hotels requires significant technical expertise and ongoing maintenance. Most hotels lack Schema.org compliance - a fundamental requirement. Additionally, the generic NLWeb protocol isn't optimized for hospitality data models like room types, availability, pricing tiers, and seasonal packages. Without proper implementation, AI assistants may misunderstand or misrepresent your property."
            },
            {
                "question": "What makes Kismet's NLWeb implementation different?",
                "answer": "Kismet has forked and extensively modified NLWeb specifically for hotels. We've rewritten the LLM logic to understand hospitality concepts like dynamic pricing, room categories, and guest preferences. Our indexing system is built around hotel data models - not generic web content. We also create and maintain RSS feeds for your property, ensuring your content stays fresh and discoverable without your team lifting a finger."
            },
            {
                "question": "What technical challenges does Kismet solve for hotels?",
                "answer": "Kismet eliminates three major technical hurdles: First, we handle all Schema.org structuring - most hotels aren't compliant and would need months of development work. Second, we've built hotel-specific AI logic that understands amenities, packages, and availability in ways generic NLWeb cannot. Third, we manage all protocol updates - as NLWeb evolves rapidly, your implementation stays current automatically without your IT team tracking changes or rewriting code."
            },
            {
                "question": "How much technical work would my hotel save by using Kismet?",
                "answer": "Implementing NLWeb properly requires a dedicated development team for 3-6 months, plus ongoing maintenance. You'd need expertise in Schema.org, RSS feeds, semantic indexing, and AI model integration. With Kismet, implementation takes days, not months. Your web team needs zero NLWeb knowledge - we handle the complex protocol work while they focus on your website and guest experience."
            },
            {
                "question": "Will Kismet keep my hotel's NLWeb implementation up to date?",
                "answer": "Yes, this is one of Kismet's key advantages. NLWeb is evolving rapidly as AI capabilities expand. When the protocol updates, when new AI platforms emerge, or when best practices change, Kismet automatically updates your implementation. Your hotel stays at the cutting edge of AI discovery without your team monitoring GitHub repos or rewriting integrations. Think of it as future-proofing your AI presence."
            },
            {
                "question": "What does Kismet charge for NLWeb implementation?",
                "answer": "For hotels that are good candidates for Kismet's full platform, we implement NLWeb at no charge. We believe in the open source ethos - some technologies should be accessible to all. There are no setup fees, monthly fees, or hidden costs for NLWeb. We invest in making your hotel AI-discoverable because we know it benefits everyone when travelers can find the perfect property through any channel they choose."
            },
            {
                "question": "Why would Kismet implement NLWeb for free?",
                "answer": "Our business model aligns perfectly with hotel interests. Kismet generates revenue only when guests book directly through our AI-powered booking platform - not from NLWeb itself. By making hotels discoverable through AI search, we help drive more direct bookings for everyone. Think of NLWeb as the foundation: it brings guests to discover your property through AI, and if they choose to book through Kismet's personalized booking experience, we earn a success fee. No bookings, no fees. This alignment means we're invested in your success, not in charging for basic AI visibility."
            }
        ]
        for i, faq in enumerate(nlweb_faqs):
            faqs.append({
                "url": f"{url}#nlweb-faq-{i+1}",
                "name": f"NLWeb FAQ: {faq['question']}",
                "@type": "Question",
                "site": SITE_NAME,
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": faq['answer']
                },
                "keywords": enhance_keywords_for_faq(faq['question'], faq['answer']),
                "description": f"NLWeb FAQ about {faq['question'].lower()}",
                "source": "nlweb_page_faq"
            })
    
    elif url.endswith('/mcp') or '/mcp#' in url:
        # MCP page FAQs (9 total)
        mcp_faqs = [
            {
                "question": "What is MCP?",
                "answer": "Model Context Protocol (MCP) is an open standard developed by Anthropic that enables AI assistants to connect with data sources and tools in real-time. Think of it as a USB-C port for AI - it provides a standardized way for AI models like Claude and ChatGPT to access your hotel's systems, check availability, quote rates, and even process bookings. MCP replaces fragmented API integrations with a single, secure protocol."
            },
            {
                "question": "How does Kismet implement MCP for hotels?",
                "answer": "Kismet uses MCP to bridge AI assistants with your hotel's PMS, booking engine, and CRM systems. When a guest asks an AI assistant about availability or wants to make a booking, MCP enables that AI to securely access your real-time data and complete transactions. This means guests can check rates, book rooms, and even modify reservations through natural conversation with AI - all while the data flows directly into your existing systems."
            },
            {
                "question": "Is MCP secure for hotel data?",
                "answer": "Yes, MCP is designed with enterprise-grade security. Kismet's MCP uses OAuth 2.1 authentication, TLS encryption for all data transfers, and granular permission controls. You decide exactly what data AI can access and what actions it can perform. All interactions are logged for complete auditability. Your sensitive data like revenue reports or guest personal information can be kept completely private while still enabling AI-powered bookings."
            },
            {
                "question": "Which hotel systems can MCP connect to?",
                "answer": "Kismet MCP integrates with major property management systems including Mews, Cloudbeds, Opera (Oracle), Stayntouch, and others. It also connects with booking engines, channel managers, CRM systems, and revenue management tools. If your system has an API, Kismet can likely integrate it through MCP. We handle all the technical connections, so you don't need to worry about compatibility."
            },
            {
                "question": "What can guests do through MCP-enabled AI?",
                "answer": "With MCP, guests can have natural conversations with AI to: check real-time room availability and rates, compare different room types and packages, make instant bookings with confirmation, modify or cancel existing reservations, inquire about amenities and services, get personalized recommendations based on preferences, and receive immediate answers about policies and facilities. All through conversational AI, without navigating websites or apps."
            },
            {
                "question": "How does MCP differ from chatbots?",
                "answer": "Traditional chatbots provide pre-programmed responses and often can't access real-time data or complete transactions. MCP-enabled AI assistants can actually check your live inventory, quote accurate prices based on current availability, apply dynamic pricing rules, and complete bookings that flow directly into your PMS. Instead of saying 'please visit our website,' MCP allows AI to say 'I found a deluxe room available for those dates at $189/night. Shall I book it for you?'"
            },
            {
                "question": "What control do I have over AI actions through MCP?",
                "answer": "You have complete control through permission settings. You can configure AI to: view-only mode (check availability but not book), quote generation (create offers but require human approval), instant booking for certain room types or rate ranges, or full autonomy with defined business rules. These permissions can be adjusted anytime through your Kismet dashboard, and you can set different permissions for different AI platforms or use cases."
            },
            {
                "question": "How long does MCP implementation take?",
                "answer": "Basic MCP implementation typically takes 1-2 weeks for single properties. This includes connecting to your PMS, testing integrations, configuring permissions, and training your team. More complex setups with multiple properties, custom workflows, or extensive system integrations may take 3-4 weeks. Kismet handles all technical aspects, so your IT team's involvement is minimal."
            },
            {
                "question": "Will MCP-enabled bookings appear in my PMS?",
                "answer": "Yes, all bookings made through MCP flow directly into your PMS just like any other direct booking. They appear with guest details, room assignments, and payment information exactly as if booked through your website. MCP bookings are direct bookings, and you can track their source for attribution. Your front desk staff will see them immediately in your regular reservation system."
            }
        ]
        for i, faq in enumerate(mcp_faqs):
            faqs.append({
                "url": f"{url}#mcp-faq-{i+1}",
                "name": f"MCP FAQ: {faq['question']}",
                "@type": "Question",
                "site": SITE_NAME,
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": faq['answer']
                },
                "keywords": enhance_keywords_for_faq(faq['question'], faq['answer']),
                "description": f"MCP FAQ about {faq['question'].lower()}",
                "source": "mcp_page_faq"
            })
    
    return faqs

async def fetch_url_content(session: aiohttp.ClientSession, url: str) -> str:
    """Fetch content from a URL."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; NLWeb-Indexer/1.0; +https://nlweb.ai)'
        }
        async with session.get(url, timeout=30, headers=headers) as response:
            if response.status == 200:
                content = await response.text()
                return content
            else:
                print(f"Failed to fetch {url}: HTTP {response.status}")
                return ""
    except Exception as e:
        print(f"Error fetching {url}: {str(e)}")
        return ""

async def extract_page_content(html: str) -> Dict[str, Any]:
    """Extract relevant content from HTML page."""
    soup = BeautifulSoup(html, 'html.parser')
    
    # Extract metadata
    title = ""
    description = ""
    
    # Try to get title
    title_tag = soup.find('title')
    if title_tag:
        title = title_tag.get_text(strip=True)
    
    # Try to get meta description
    meta_desc = soup.find('meta', attrs={'name': 'description'})
    if meta_desc:
        description = meta_desc.get('content', '')
    
    # Extract main content
    # Remove script and style elements EXCEPT JSON-LD
    for element in soup(["script", "style"]):
        # Keep JSON-LD scripts
        if element.name == "script" and element.get("type") == "application/ld+json":
            continue
        element.decompose()
    
    # Get text content
    text_content = soup.get_text()
    # Clean up whitespace
    lines = (line.strip() for line in text_content.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text_content = ' '.join(chunk for chunk in chunks if chunk)
    
    # Look for JSON-LD structured data
    structured_data = []
    json_ld_scripts = soup.find_all('script', attrs={'type': 'application/ld+json'})
    
    # Process JSON-LD scripts in reverse order to prioritize page-specific FAQs
    # (they're often added later via JavaScript and appear after the root layout FAQs)
    for script in reversed(json_ld_scripts):
        try:
            script_text = script.string or script.get_text()
            if script_text:
                script_text = script_text.strip()
                data = json.loads(script_text)
                structured_data.append(data)
        except json.JSONDecodeError:
            continue
        except Exception:
            continue
    
    return {
        "title": title,
        "description": description,
        "text": text_content[:5000],  # Limit text length
        "structured_data": structured_data
    }

async def fetch_sitemap_urls(session: aiohttp.ClientSession) -> List[str]:
    """Fetch and parse sitemap to get URLs."""
    sitemap_content = await fetch_url_content(session, SITEMAP_URL)
    if not sitemap_content:
        print("Failed to fetch sitemap")
        return []
    
    urls = []
    try:
        root = ET.fromstring(sitemap_content)
        namespace = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        
        for url_elem in root.findall('.//sm:url/sm:loc', namespace):
            urls.append(url_elem.text)
    except Exception as e:
        print(f"Error parsing sitemap: {str(e)}")
    
    return urls

async def fetch_rss_urls(session: aiohttp.ClientSession) -> List[Dict[str, str]]:
    """Fetch and parse RSS feed to get additional URLs and metadata."""
    rss_content = await fetch_url_content(session, RSS_FEED_URL)
    if not rss_content:
        print("Failed to fetch RSS feed")
        return []
    
    items = []
    try:
        feed = feedparser.parse(rss_content)
        for entry in feed.entries:
            # Skip YouTube and external links for now
            if 'youtube.com' in entry.link or 'linkedin.com' in entry.link:
                continue
                
            items.append({
                'url': entry.link,
                'title': entry.title,
                'description': entry.description,
                'content': entry.get('content', [{}])[0].get('value', '') if entry.get('content') else ''
            })
    except Exception as e:
        print(f"Error parsing RSS feed: {str(e)}")
    
    return items

def create_platform_feature_documents() -> List[Dict[str, Any]]:
    """Create documents for Kismet platform features that exist but aren't on the website."""
    
    documents = []
    
    # Email Dashboard Feature
    email_dashboard_doc = {
        "url": "https://www.makekismet.com/features/email-dashboard",
        "name": "Kismet Email Dashboard - Personalized Guest Outreach",
        "@type": "WebPage",
        "site": SITE_NAME,
        "description": "The Kismet Email Dashboard enables hotels to send personalized offers to guests and groups with one-click functionality for instant engagement.",
        "text": """
        The Kismet Email Dashboard is a powerful tool for personalized guest outreach and communication. 
        
        Key Features:
        - Quick Response functionality for instant guest engagement
        - Personalized email campaigns tailored to individual guests
        - One-click email sending with pre-built templates
        - Guest conversation management and tracking
        - Automated personalized offers based on guest preferences
        - Email inbox and sent message management
        - Integration with guest booking history and preferences
        
        The dashboard shows real-time email conversations with guests, allowing hotels to:
        - Send exclusive offers directly to specific guests
        - Manage ongoing email conversations
        - Track email engagement and responses
        - Create personalized subject lines and content
        - Send targeted offers like "OTA-Free Weekend" promotions
        - Welcome back returning guests with customized offers
        
        Examples of personalized emails include:
        - "Enjoy an OTA-Free Weekend at Knollcroft - Exclusive Offer for Booking.com"
        - "Welcome Back to Knollcroft: Your Cozy Catskills Retreat Awaits"
        - "Discover Cozy Luxury at Knollcroft - A Special Offer for You"
        - "Exclusive Private Booking Opportunity at Knollcroft Just for You"
        
        All emails are marked as "Personalized" and can be edited before sending, giving hotels full control over their guest communication.
        """,
        "keywords": enhance_keywords_for_faq("Email Dashboard", "Personalized guest outreach and email marketing"),
        "source": "platform_feature"
    }
    
    # Marketing Lists Feature
    marketing_lists_doc = {
        "url": "https://www.makekismet.com/features/marketing-lists",
        "name": "Kismet Marketing Lists - Build Your Guest Database",
        "@type": "WebPage", 
        "site": SITE_NAME,
        "description": "Kismet Marketing Lists help hotels build and manage their marketing contact database with powerful segmentation and engagement tracking.",
        "text": """
        Kismet Marketing Lists provide comprehensive contact management and guest database functionality for hotels.
        
        Key Metrics and Features:
        - Total Contacts tracking (e.g., 3,847 contacts)
        - New Contacts monitoring (e.g., 476 in last 30 days, +28.3% growth)
        - Current Engagement rates (e.g., 61.2% of total audience)
        - Historical engagement tracking and trends
        
        Contact Management Features:
        - Search and filter contacts by multiple criteria
        - Time period filtering (Last 30 Days, custom date ranges)
        - Status filtering (All, Engaged, etc.)
        - Source tracking (Website, Instagram, Referral)
        - Segment classification (Luxury, Business, Family)
        - Contact method tracking (Email, Phone, Instagram)
        
        Guest Database Capabilities:
        - Individual contact profiles with full history
        - Multiple contact methods per guest (email, phone, social)
        - Source attribution (Website visits, Instagram engagement, Referrals)
        - Engagement status tracking (Engaged, Active, etc.)
        - Date added tracking for contact lifecycle management
        - Saved Lists functionality for targeted campaigns
        
        Segmentation Options:
        - Luxury travelers
        - Business guests  
        - Family segments
        - Custom segments based on behavior and preferences
        
        The system tracks contact growth over time, showing percentage increases and historical averages, helping hotels understand their marketing reach and guest engagement trends.
        
        Integration with other Kismet features allows for:
        - Targeted email campaigns to specific segments
        - Personalized offers based on guest history
        - Cross-channel engagement tracking
        - ROI measurement for marketing efforts
        """,
        "keywords": enhance_keywords_for_faq("Marketing Lists", "Guest database and contact management with segmentation"),
        "source": "platform_feature"
    }
    
    documents.extend([email_dashboard_doc, marketing_lists_doc])
    
    # Create FAQ documents for these features
    feature_faqs = [
        {
            "question": "How does the Email Dashboard help with guest outreach?",
            "answer": "The Email Dashboard enables personalized guest communication with quick response functionality, automated personalized offers, and one-click email sending. Hotels can manage ongoing conversations, send exclusive offers, and track engagement all from a single interface."
        },
        {
            "question": "What can I track with Marketing Lists?",
            "answer": "Marketing Lists provide comprehensive contact analytics including total contacts, new contact growth rates, engagement percentages, and historical trends. You can segment guests by luxury/business/family categories, track multiple contact methods, and monitor source attribution from website, Instagram, and referrals."
        },
        {
            "question": "How do I segment my guest database?",
            "answer": "Kismet automatically segments guests into categories like Luxury, Business, and Family based on their behavior and preferences. You can also create custom segments, filter by engagement status, contact source, and date ranges to target specific guest groups for campaigns."
        },
        {
            "question": "Can I send personalized emails to specific guests?",
            "answer": "Yes, the Email Dashboard allows you to send highly personalized emails to individual guests or segments. All emails are marked as 'Personalized' and can be edited before sending. Examples include exclusive offers, welcome back messages, and targeted promotions based on guest history."
        }
    ]
    
    # Add FAQ documents
    for i, faq in enumerate(feature_faqs):
        keywords = enhance_keywords_for_faq(faq['question'], faq['answer'])
        faq_doc = {
            "url": f"https://www.makekismet.com/features/faq#{i+1}",
            "name": f"FAQ: {faq['question']}",
            "@type": "Question",
            "site": SITE_NAME,
            "acceptedAnswer": {
                "@type": "Answer",
                "text": faq['answer']
            },
            "keywords": keywords,
            "description": f"FAQ about {faq['question'].lower()}",
            "source": "platform_feature"
        }
        documents.append(faq_doc)
    
    return documents

def create_sales_faq_documents() -> List[Dict[str, Any]]:
    """Create documents for sales-specific FAQs that are client-side rendered."""
    
    documents = []
    
    sales_faqs = [
        {
            "question": "How does Kismet help my sales team spend less time on unqualified leads?",
            "answer": "Kismet automatically qualifies leads using your hotel's past conversion data and real-time availability, ensuring your sales team only spends time on prospects with genuine booking intent and budget fit."
        },
        {
            "question": "What types of leads does Kismet generate - are they mainly transient guests or group/corporate bookings?",
            "answer": "Kismet specializes in leisure and social group segments—particularly smaller social groups that traditional sales processes often miss. We help you capture and nurture these high-value prospects with minimal manual effort from your sales team."
        },
        {
            "question": "How does Kismet integrate with our existing CRM and sales processes?",
            "answer": "Kismet integrates seamlessly with Tripleseat and Event Temple (in beta). For smaller properties, Kismet's built-in CRM capabilities are robust enough to serve as your primary sales management system."
        },
        {
            "question": "Can Kismet help with group RFPs and meeting planner outreach?",
            "answer": "Yes, Kismet streamlines RFP processing from both form submissions and natural language inquiries—whether through chat, email, or social media—and automatically drafts personalized initial responses for your review."
        },
        {
            "question": "How much time will my sales team save per week using Kismet?",
            "answer": "Hotels using Kismet typically cut sales busywork in half, saving an average of 10 hours per week. This lets your team focus on closing deals instead of chasing unqualified leads."
        },
        {
            "question": "Does Kismet provide sales attribution - can we track which channels generate the best converting leads?",
            "answer": "Attribution is core to what we do. Social groups are notoriously difficult to track due to long lead times and informal booking processes. Kismet shows you exactly which Instagram posts, ads, or touchpoints drive leads—and whether they actually convert to bookings."
        },
        {
            "question": "How does Kismet handle lead scoring and qualification criteria?",
            "answer": "Our proprietary lead scoring model analyzes your hotel's historical sales data combined with real-time contribution and displacement analysis, ensuring you prioritize prospects most likely to book and generate incremental revenue."
        },
        {
            "question": "Can our sales team customize offers and pricing for leads generated by Kismet?",
            "answer": "Absolutely. Kismet gives you the control on pricing and packaging as well as which types of leads to offer instant-book to and which will require personal touch."
        },
        {
            "question": "How do I make sure AI can find my hotel?",
            "answer": "To ensure AI discovery, hotels need to integrate Natural Language Web (NLWeb) and Model Context Protocol (MCP) best practices. Specifically, this means: 1) Maintain updated structured data (Schema.org markup) on their website, 2) Keep RSS feeds current with fresh content, 3) Allow AI crawlers like GPTBot and PerplexityBot access via robots.txt, 4) Publish regular content about amenities, local attractions, and unique offerings, and 5) Ensure their booking engine and website have clear, semantic HTML markup that AI can understand."
        },
        {
            "question": "How does Kismet increase direct bookings?",
            "answer": "Kismet increases direct bookings by offering guests a private booking channel with offers just for them. Specifically, this involves: 1) Identifying guests early in their search journey across social media, web, and email, 2) Creating personalized private-rate offers that aren't available on OTAs, 3) Using AI to match guests with relevant packages and experiences, 4) Converting social media interest into attributable bookings through natural language conversations, and 5) Building owned marketing audiences that reduce dependence on third-party channels while increasing repeat bookings."
        },
        {
            "question": "Does Kismet replace my booking engine?",
            "answer": "No, Kismet doesn't replace your booking engine, PMS, or CRS. Kismet is a lightweight AI layer that integrates with your existing systems through standard APIs. It enhances your current tech stack by adding conversational AI capabilities and intelligent guest matching, while all bookings flow through your existing booking engine and reservations appear in your current PMS. No software gets ripped out - Kismet just makes your existing systems smarter."
        }
    ]
    
    # Create FAQ documents
    for i, faq in enumerate(sales_faqs):
        keywords = enhance_keywords_for_faq(faq['question'], faq['answer'])
        
        # Add sales-specific keywords
        keywords.extend([
            'sales team', 'lead generation', 'lead qualification', 'sales process',
            'CRM integration', 'group bookings', 'RFP', 'sales attribution',
            'lead scoring', 'sales automation', 'AI discovery', 'SEO for hotels',
            'direct bookings', 'booking engine integration'
        ])
        
        faq_doc = {
            "url": f"https://www.makekismet.com/sales#faq-{i+1}",
            "name": f"Sales FAQ: {faq['question']}",
            "@type": "Question",
            "site": SITE_NAME,
            "acceptedAnswer": {
                "@type": "Answer",
                "text": faq['answer']
            },
            "keywords": list(set(keywords)),  # Remove duplicates
            "description": f"Sales FAQ about {faq['question'].lower()}",
            "source": "sales_faq"
        }
        documents.append(faq_doc)
    
    return documents

async def create_comprehensive_documents(sitemap_urls: List[str], rss_items: List[Dict[str, str]], local_resources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Create NLWeb-compatible documents from all sources."""
    documents = []
    processed_urls: Set[str] = set()
    
    # Add local resources first
    documents.extend(local_resources)
    for resource in local_resources:
        processed_urls.add(resource['url'])
    
    async with aiohttp.ClientSession() as session:
        # Process sitemap URLs
        for url in sitemap_urls:
            if url in processed_urls:
                continue
                
            print(f"Processing sitemap URL: {url}")
            
            # Skip RSS feed URL itself
            if url.endswith('feed.xml'):
                processed_urls.add(url)
                continue
            
            # Skip PDF files that we've already processed locally
            if url.endswith('.pdf'):
                # Check if we already have this PDF from local resources
                pdf_name = url.split('/')[-1]
                if any(pdf_name in resource['url'] for resource in local_resources):
                    print(f"PDF {pdf_name} already processed from local resources")
                    processed_urls.add(url)
                    continue
                
                # If not found locally, create a basic reference
                documents.append({
                    "url": url,
                    "name": f"Kismet Resource: {pdf_name}",
                    "@type": "PresentationDigitalDocument",
                    "description": f"Kismet resource document: {pdf_name}",
                    "site": SITE_NAME,
                    "keywords": enhance_keywords_for_content(pdf_name, "Kismet resource", "hotel AI platform")
                })
                processed_urls.add(url)
                continue
            
            # Fetch and process HTML pages
            html_content = await fetch_url_content(session, url)
            if html_content:
                page_data = await extract_page_content(html_content)
                
                # Create base document
                doc = {
                    "url": url,
                    "name": page_data["title"] or f"Page at {url}",
                    "description": page_data["description"],
                    "text": page_data["text"],
                    "site": SITE_NAME,
                    "@type": "WebPage",
                    "keywords": enhance_keywords_for_content(
                        page_data["title"], 
                        page_data["description"], 
                        page_data["text"]
                    )
                }
                
                # Get page-specific FAQs based on URL
                page_faqs = get_page_specific_faqs(url)
                if page_faqs:
                    print(f"Added {len(page_faqs)} page-specific FAQs for {url}")
                    documents.extend(page_faqs)
                else:
                    # Process structured data for FAQs (for homepage and other pages)
                    if page_data["structured_data"]:
                        for sd in page_data["structured_data"]:
                            if isinstance(sd, dict):
                                # Extract individual FAQ documents
                                if sd.get("@type") == "FAQPage" and sd.get("mainEntity"):
                                    print(f"Found FAQPage with {len(sd['mainEntity'])} questions")
                                    for i, question in enumerate(sd["mainEntity"]):
                                        if question.get("@type") == "Question":
                                            question_name = question.get("name", "")
                                            answer_text = question.get("acceptedAnswer", {}).get("text", "")
                                            
                                            # Generate enhanced keywords
                                            keywords = enhance_keywords_for_faq(question_name, answer_text)
                                            
                                            # Create individual FAQ document
                                            faq_doc = {
                                                "url": f"{url}#faq-{i+1}",
                                                "name": f"FAQ: {question_name}",
                                                "@type": "Question",
                                                "site": SITE_NAME,
                                                "acceptedAnswer": question.get("acceptedAnswer", {}),
                                                "keywords": keywords,
                                                "description": f"FAQ about {question_name.lower()}"
                                            }
                                            
                                            documents.append(faq_doc)
                                            print(f"Created FAQ #{i+1}: {question_name}")
                                
                                # Merge other structured data
                                else:
                                    for key in ["@type", "offers", "publisher", "applicationCategory", "operatingSystem"]:
                                        if key in sd and key not in doc:
                                            doc[key] = sd[key]
                
                documents.append(doc)
                processed_urls.add(url)
            
            await asyncio.sleep(0.5)
        
        # Process RSS items for additional content
        for item in rss_items:
            url = item['url']
            if url in processed_urls:
                continue
                
            print(f"Processing RSS item: {url}")
            
            # For RSS items not in sitemap, fetch content
            html_content = await fetch_url_content(session, url)
            if html_content:
                page_data = await extract_page_content(html_content)
                
                # Create document with RSS metadata + fetched content
                doc = {
                    "url": url,
                    "name": item['title'] or page_data["title"] or f"Page at {url}",
                    "description": item['description'] or page_data["description"],
                    "text": page_data["text"] or item['content'],
                    "site": SITE_NAME,
                    "@type": "WebPage",
                    "keywords": enhance_keywords_for_content(
                        item['title'], 
                        item['description'], 
                        item['content'] + " " + page_data["text"]
                    ),
                    "source": "rss_feed"
                }
                
                documents.append(doc)
                processed_urls.add(url)
                print(f"Added RSS content: {item['title']}")
            
            await asyncio.sleep(0.5)
    
    # Add platform feature documents
    platform_features = create_platform_feature_documents()
    documents.extend(platform_features)
    
    # Add sales-specific FAQ documents
    sales_faqs = create_sales_faq_documents()
    documents.extend(sales_faqs)
    
    return documents

async def save_documents_to_file(documents: List[Dict[str, Any]], filename: str):
    """Save documents to a JSON file in the format expected by db_load."""
    output_lines = []
    
    for doc in documents:
        url = doc.get("url", "")
        doc_copy = doc.copy()
        if "url" in doc_copy:
            del doc_copy["url"]
        
        json_str = json.dumps(doc_copy, ensure_ascii=False)
        output_lines.append(f"{url}\t{json_str}")
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output_lines))
    
    print(f"Saved {len(documents)} documents to {filename}")

async def main():
    """Main function to orchestrate comprehensive indexing with PDF support."""
    print(f"Starting comprehensive Kismet indexing with PDF support at {datetime.now()}")
    
    # Scan local resources first
    local_resources = scan_local_resources()
    print(f"Found {len(local_resources)} local PDF resources")
    
    async with aiohttp.ClientSession() as session:
        # Fetch from web sources
        sitemap_urls = await fetch_sitemap_urls(session)
        rss_items = await fetch_rss_urls(session)
    
    print(f"Found {len(sitemap_urls)} URLs in sitemap")
    print(f"Found {len(rss_items)} items in RSS feed")
    
    # Create comprehensive documents
    documents = await create_comprehensive_documents(sitemap_urls, rss_items, local_resources)
    
    print(f"Created {len(documents)} total documents ({len(local_resources)} PDFs, {len(create_platform_feature_documents())} platform features, {len(create_sales_faq_documents())} sales FAQs)")
    
    # Save to temporary file
    temp_file = "/tmp/kismet_comprehensive_with_pdfs.json"
    await save_documents_to_file(documents, temp_file)
    
    # Delete existing data for the site
    print(f"Deleting existing data for site '{SITE_NAME}'...")
    try:
        await delete_site_from_database(SITE_NAME)
    except Exception as e:
        print(f"Warning: Could not delete existing data: {e}")
    
    # Load new data into NLWeb
    print(f"Loading comprehensive data with PDFs into NLWeb...")
    try:
        await loadJsonToDB(
            file_path=temp_file,
            site=SITE_NAME,
            batch_size=100,
            delete_existing=False,
            force_recompute=True
        )
        print("Successfully indexed comprehensive Kismet content with PDFs!")
    except Exception as e:
        print(f"Error loading data into NLWeb: {e}")
        raise
    
    print(f"Temp file kept at: {temp_file}")

if __name__ == "__main__":
    asyncio.run(main()) 