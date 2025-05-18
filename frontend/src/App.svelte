<script lang="ts">
  import { onMount } from 'svelte';

  let articles: any[] = [];
  let error = '';
  let loading = true;
  let user: any = null;

  let commentInputs: Record<string, string> = {};
  let commentLists: Record<string, any[]> = {};
  let posting: Record<string, boolean> = {};

  const deduplicateArticles = (articles: any[]): any[] => {
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

  const filterRelevantArticles = (articles: any[]): any[] => {
    return articles.filter(article => {
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

  const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

  const fetchLocalNews = async (apiKey: string): Promise<any[]> => {
    const searchTerms = [
      '"Davis, California"',
      '"UC Davis"',
      '"University of California, Davis"',
      '"Sacramento"',
      '"Yolo County"',
      '"West Sacramento"',
      '"Woodland"',
      '"Northern California"'
    ];

    const allArticles: any[] = [];

    for (const term of searchTerms) {
      const url = `https://api.nytimes.com/svc/search/v2/articlesearch.json?q=${term}&begin_date=20230101&sort=newest&api-key=${apiKey}`;
      const res = await fetch(url);
      const data = await res.json();
      if (data.response?.docs) {
        allArticles.push(...data.response.docs);
      }
      await sleep(300);
    }

    const unique = allArticles.filter(
      (a, i, self) => i === self.findIndex(b => b._id === a._id)
    );

    const relevant = filterRelevantArticles(unique);
    relevant.sort((a, b) => new Date(b.pub_date).getTime() - new Date(a.pub_date).getTime());
    return deduplicateArticles(relevant);
  };

  const getImageUrl = (media: any[] | undefined): string | null => {
    if (!Array.isArray(media)) return null;
    const item = media.find((m) =>
      m.subtype === "xlarge" || m.subtype === "largeHorizontal375" || m.url
    );
    if (!item || !item.url) return null;
    return item.url.startsWith('http')
      ? item.url
      : `https://www.nytimes.com/${item.url}`;
  };

  const fetchComments = async (url: string) => {
    const res = await fetch(`/api/comments?url=${encodeURIComponent(url)}`);
    const data = await res.json();
    commentLists[url] = data;
  };

  const postComment = async (url: string) => {
    const text = commentInputs[url]?.trim();
    if (!text) return;
    posting[url] = true;

    const res = await fetch('/api/comments', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ article_url: url, text })
    });

    if (res.ok) {
      commentInputs[url] = '';
      await fetchComments(url);
    }

    posting[url] = false;
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

    // ✅ Proper login detection
    try {
      const res = await fetch('/api/user');
      if (res.ok) {
        user = await res.json();
      }
    } catch {
      user = null;
    }

    for (const article of articles) {
      fetchComments(article.web_url);
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
                  weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
                })}
              {:else}
                Date unavailable
              {/if}
            </p>
            <p class="article-snippet">{article.snippet}</p>
          </article>
        </a>

        <!-- 💬 Comment section -->
        <div style="padding: 10px 0;" class="article-body">
          <h4>Comments:</h4>

          {#if commentLists[article.web_url]?.length > 0}
            <ul>
              {#each commentLists[article.web_url] as c}
                <li style="margin-bottom: 8px;">
                  <strong>{c.author_email}</strong>
                  <em> ({new Date(c.timestamp).toLocaleString()})</em><br>
                  {c.text}
                </li>
              {/each}
            </ul>
          {:else}
            <p style="color: gray;">No comments yet.</p>
          {/if}

          {#if user}
            <textarea
              bind:value={commentInputs[article.web_url]}
              rows="2"
              placeholder="Write a comment..."
              style="width: 100%; margin-top: 8px;"
            ></textarea>
            <button on:click={() => postComment(article.web_url)} disabled={posting[article.web_url]}>
              {posting[article.web_url] ? 'Posting...' : 'Post Comment'}
            </button>
          {:else}
            <p style="font-size: 0.9rem; color: gray;">Login to post a comment.</p>
          {/if}
        </div>
      {/each}
    {/if}
  </div>

  <footer class="footer">
    <p>© 2025 The New York Times Company. All rights reserved.</p>
  </footer>
</main>

<style src="./style.css"></style>
