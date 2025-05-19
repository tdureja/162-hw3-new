<script lang="ts">
  // import a lifecycle function from svelte to run code after the component mounts
  import { onMount } from 'svelte';

  // these are reactive variables to store articles, user info, and state like loading and errors
  let articles: any[] = [];
  let error = '';
  let loading = true;
  let user: any = null;

  // setting up dictionaries for comment inputs, lists of comments per article, and loading states for posting
  let commentInputs: Record<string, string> = {};
  let commentLists: Record<string, any[]> = {};
  let posting: Record<string, boolean> = {};
  let isModerator = false;

  // redirects user to login page when login button is clicked
  function login() {
    window.location.href = 'http://localhost:8000/login';
  }

  // removes duplicate articles based on headline title
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

  // keeps only the articles that mention relevant local areas like davis or sacramento
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

  // helper function to pause execution for a bit (used to avoid rate limits)
  const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

  // fetches local news articles from the nytimes api for specific search terms
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
      await sleep(300); // slow down requests to be polite to the API
    }

    // remove duplicate articles based on their unique _id
    const unique = allArticles.filter(
      (a, i, self) => i === self.findIndex(b => b._id === a._id)
    );

    // filter and sort articles by most recent first
    const relevant = filterRelevantArticles(unique);
    relevant.sort((a, b) => new Date(b.pub_date).getTime() - new Date(a.pub_date).getTime());
    return deduplicateArticles(relevant);
  };

  // tries to grab the best image url for an article if available
  const getImageUrl = (article: any): string | null => {
    const media = article.multimedia;
    if (!Array.isArray(media) || media.length === 0) return null;

    const item = media.find((m) => m.subtype === 'xlarge') || media[0];

    return item?.url
      ? `https://www.nytimes.com/${item.url}`
      : null;
  };

  // fetches comments for a specific article url and stores them in the commentLists
  const fetchComments = async (url: string) => {
    const res = await fetch(`/api/comments?url=${encodeURIComponent(url)}`);
    const data = await res.json();
    commentLists[url] = data;
  };

  // handles posting a comment for a given article
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
      await fetchComments(url); // refresh the comment list after posting
    }

    posting[url] = false;
  };

  // lets a moderator delete a comment by its id
  const deleteComment = async (commentId: string) => {
    const res = await fetch('/api/moderate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: commentId })
    });

    if (res.ok) {
      // refresh comments for all articles
      for (const article of articles) {
        await fetchComments(article.web_url);
      }
    }
  };

  // runs automatically when the component mounts
  onMount(async () => {
    // try to fetch the nytimes api key and load news articles
    try {
      const res = await fetch('/api/key');
      const { apiKey } = await res.json();
      articles = await fetchLocalNews(apiKey);
    } catch (err) {
      error = 'Failed to load articles.';
    } finally {
      loading = false;
    }

    // try to fetch the logged-in user info
    try {
      const res = await fetch('/api/user');
      if (res.ok) {
        const data = await res.json();
        user = data;
        isModerator = user?.email?.includes('mod') || false;
      }
    } catch {
      user = null;
    }

    // load comments for each article
    for (const article of articles) {
      fetchComments(article.web_url);
    }
  });
</script>

<main>
  <header>
    {#if !user}
      <!-- show login button if the user isn't logged in -->
      <div style="margin: 1rem;">
        <button on:click={login}>Login</button>
      </div>
    {/if}

    <!-- site title and date header bar -->
    <div class="meta-bar">
      <div class="date-block">
        <span>{new Date().toDateString()}</span>
        <span class="todays-paper">Today's Paper</span>
      </div>
      <h1>The New York Times</h1>
    </div>

    <!-- nav bar with categories -->
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

  <!-- decorative line under the nav bar -->
  <div class="nav-underline"></div>

  <!-- main article section -->
  <div class="content-grid">
    <h3 class="section-label">Local News</h3>

    {#if loading}
      <!-- loading state -->
      <p class="article-body" style="grid-column: 1 / -1;">Loading...</p>
    {:else if error}
      <!-- error message if something went wrong -->
      <p class="article-body" style="grid-column: 1 / -1;">{error}</p>
    {:else if articles.length === 0}
      <!-- fallback message if no articles are found -->
      <p class="article-body" style="grid-column: 1 / -1;">
        No articles found about the Davis/Sacramento region.
      </p>
    {:else}
      <!-- loop through and show up to 8 articles -->
      {#each articles.slice(0, 8) as article}
        <!-- each article links to its source -->
        <a class="article-link-wrapper" href={article.web_url} target="_blank">
          <article class="article-card">
            <!-- optional image -->
            <div class="article-image">
              {#if getImageUrl(article)}
                <img src={getImageUrl(article)} alt={article.headline?.main} />
              {/if}
            </div>
            <!-- article title and snippet -->
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

        <!-- comments section for each article -->
        <div style="padding: 10px 0;" class="article-body">
          <h4>Comments:</h4>

          {#if commentLists[article.web_url]?.length > 0}
            <!-- show list of comments -->
            <ul>
              {#each commentLists[article.web_url] as c}
                <li style="margin-bottom: 8px;">
                  <strong>{c.author_email}</strong>
                  <em> ({new Date(c.timestamp).toLocaleString()})</em><br>
                  {c.text}
                  {#if isModerator}
                    <!-- show remove button if user is a moderator -->
                    <button
                      style="margin-left: 8px; font-size: 0.75rem;"
                      on:click={() => deleteComment(c.id)}
                    >
                      Remove
                    </button>
                  {/if}
                </li>
              {/each}
            </ul>
          {:else}
            <!-- no comments yet -->
            <p style="color: gray;">No comments yet.</p>
          {/if}

          <!-- comment form or login prompt -->
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

  <!-- footer at the bottom of the page -->
  <footer class="footer">
    <p>© 2025 The New York Times Company. All rights reserved.</p>
  </footer>
</main>

<!-- bring in the styles from a separate css file -->
<style src="./style.css"></style>
