<script lang="ts">
  import { onMount } from 'svelte';

  type NYTArticle = {
    _id: string;
    web_url: string;
    headline?: { main?: string };
    pub_date?: string;
    snippet?: string;
    multimedia?: any[];
  };

  let articles: NYTArticle[] = [];
  let error: string = '';
  let loading: boolean = true;

  const deduplicateArticles = (articles: NYTArticle[]): NYTArticle[] => {
    const seen = new Set();
    return articles.filter((a) => {
      const title = a.headline?.main?.trim();
      if (title && !seen.has(title)) {
        seen.add(title);
        return true;
      }
      return false;
    });
  };

  const filterRelevantArticles = (articles: NYTArticle[]): NYTArticle[] => {
    return articles.filter((article) => {
      const text = `${article.headline?.main ?? ''} ${article.snippet ?? ''}`.toLowerCase();
      return (
        text.includes("davis") ||
        text.includes("uc davis") ||
        text.includes("university of california, davis") ||
        text.includes("sacramento") ||
        text.includes("yolo county") ||
        text.includes("west sacramento") ||
        text.includes("woodland")
      );
    });
  };

  const fetchLocalNews = async (apiKey: string): Promise<NYTArticle[]> => {
    const searchTerms = [
      '"Davis, California"',
      '"UC Davis"',
      '"University of California, Davis"',
      '"Sacramento"',
      '"Yolo County"',
      '"West Sacramento"',
      '"Woodland"',
      '"Northern California"',
    ];

    const allArticles: NYTArticle[] = [];

    for (const term of searchTerms) {
      const url = `https://api.nytimes.com/svc/search/v2/articlesearch.json?q=${term}&begin_date=20230101&sort=newest&api-key=${apiKey}`;
      const res = await fetch(url);
      const data = await res.json();
      if (data.response?.docs) {
        allArticles.push(...data.response.docs);
      }
    }

    const unique = allArticles.filter(
      (a, i, self) => i === self.findIndex((b) => b._id === a._id)
    );

    const relevant = filterRelevantArticles(unique);
    relevant.sort((a, b) => new Date(b.pub_date!).getTime() - new Date(a.pub_date!).getTime());

    return deduplicateArticles(relevant);
  };

  const getImageUrl = (media: any[] | undefined): string | null => {
    if (Array.isArray(media)) {
      const found = media.find((m) => m.url);
      return found
        ? found.url.startsWith('http')
          ? found.url
          : `https://www.nytimes.com/${found.url}`
        : null;
    }
    return null;
  };

  onMount(async () => {
    try {
      const res = await fetch('/api/key');
      const { apiKey } = await res.json();
      articles = await fetchLocalNews(apiKey);
    } catch (err) {
      error = 'Failed to load articles.';
    } finally {
      loading = false;
    }
  });
</script>

<main>
  <header>
    <div class="meta-bar">
      <div class="date-block">
        <span>{new Date().toDateString()}</span>
        <span class="todays-paper">Today's Paper</span>
      </div>
      <h1>The New York Times</h1>
    </div>

    <nav class="nav-bar">
      <span class="nav-item">U.S.</span>
      <span class="nav-item">World</span>
      <span class="nav-item">Business</span>
      <span class="nav-item">Arts</span>
      <span class="nav-item">Lifestyle</span>
      <span class="nav-item">Opinion</span>
      <span class="nav-item">Audio</span>
      <span class="nav-item">Games</span>
      <span class="nav-item">Cooking</span>
      <span class="nav-item">Wirecutter</span>
      <span class="nav-item">The Athletic</span>
    </nav>
  </header>

  <div class="nav-underline"></div>

  <div class="content-grid">
    <h3 class="section-label">Local News</h3>

    {#if loading}
      <p class="article-body" style="grid-column: 1 / -1;">Loading...</p>
    {:else if error}
      <p class="article-body" style="grid-column: 1 / -1;">{error}</p>
    {:else if articles.length === 0}
      <p class="article-body" style="grid-column: 1 / -1;">
        No articles found about the Davis/Sacramento region.
      </p>
    {:else}
      {#each articles.slice(0, 8) as article}
        <a class="article-link-wrapper" href={article.web_url} target="_blank">
          <article class="article-card">
            <div class="article-image">
              {#if getImageUrl(article.multimedia)}
                <img src={getImageUrl(article.multimedia)} alt={article.headline?.main} />
              {/if}
            </div>
            <h2 class="article-title">{article.headline?.main}</h2>
            <p class="article-date">
              {#if article.pub_date}
                {new Date(article.pub_date).toLocaleDateString('en-US', {
                  weekday: 'long',
                  year: 'numeric',
                  month: 'long',
                  day: 'numeric'
                })}
              {:else}
                Date unavailable
              {/if}
            </p>
            <p class="article-snippet">{article.snippet}</p>
          </article>
        </a>
      {/each}
    {/if}
  </div>

  <footer class="footer">
    <p>© 2025 The New York Times Company. All rights reserved.</p>
  </footer>
</main>

<style src="../static/style.css"></style>
