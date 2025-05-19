<script lang="ts">
	import { onMount } from 'svelte';
  
	let articles: any[] = [];
	let error = '';
	let loading = true;
	let user: any = null;
	let commentInputs: Record<string, string> = {};
	let commentLists: Record<string, any[]> = {};
	let posting: Record<string, boolean> = {};
	let isModerator = false;
  
	function login() {
	  window.location.href = 'http://localhost:8000/login';
	}
  
	// removes articles with duplicate headlines
	function deduplicateArticles(articles: any[]) {
	  const seen = new Set();
	  const unique = [];
	  for (const a of articles) {
		const title = a.headline?.main?.trim();
		if (title && !seen.has(title)) {
		  seen.add(title);
		  unique.push(a);
		}
	  }
	  return unique;
	}
  
	// filter to only include articles relevant to davis/sac region
	function filterRelevantArticles(articles: any[]) {
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
	}
  
	// fetch articles from api using location related search terms
	async function fetchLocalNews(apiKey: string) {
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
  
	  try {
		const allArticles = [];
  
		for (const term of searchTerms) {
		  const url = `https://api.nytimes.com/svc/search/v2/articlesearch.json?q=${term}&begin_date=20230101&sort=newest&api-key=${apiKey}`;
		  const response = await fetch(url);
		  const data = await response.json();
  
		  if (data.response && Array.isArray(data.response.docs)) {
			allArticles.push(...data.response.docs);
		  }
		}
  
		const uniqueArticles = allArticles.filter((article, index, self) =>
		  index === self.findIndex(a => a._id === article._id)
		);
  
		const relevantArticles = filterRelevantArticles(uniqueArticles);  
		relevantArticles.sort((a, b) => new Date(b.pub_date).getTime() - new Date(a.pub_date).getTime());
		const filteredArticles = deduplicateArticles(relevantArticles);
		return filteredArticles;
  
	  } catch (error) {
		console.error('Error fetching news:', error);
		throw error;
	  }
	}
  
	function getImageUrl(article: any): string | null {
	  if (Array.isArray(article.multimedia)) {
		const imageData = article.multimedia.find(m => m.url);
		if (imageData) {
		  return imageData.url.startsWith('http')
			? imageData.url
			: `https://www.nytimes.com/${imageData.url}`;
		}
	  }
	  
	  if (article.multimedia?.default?.url) {
		return article.multimedia.default.url;
	  } else if (article.multimedia?.thumbnail?.url) {
		return article.multimedia.thumbnail.url;
	  }
	  
	  return null;
	}
  
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
  
	const deleteComment = async (commentId: string) => {
	  const res = await fetch('/api/moderate', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ id: commentId })
	  });
  
	  if (res.ok) {
		for (const article of articles) {
		  await fetchComments(article.web_url);
		}
	  }
	};
  
	onMount(async () => {
	  try {
		const keyResponse = await fetch('/api/key');
		if (!keyResponse.ok) {
		  throw new Error(`Error fetching API key: ${keyResponse.status}`);
		}
		const keyData = await keyResponse.json();
		const apiKey = keyData.apiKey;
  
		articles = await fetchLocalNews(apiKey);
	  } catch (err) {
		error = 'Failed to load articles. Please try again later.';
		console.error(err);
	  } finally {
		loading = false;
	  }
  
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
  
	  for (const article of articles) {
		fetchComments(article.web_url);
	  }
	});
  </script>
  
  <main>
	<header>
	  {#if !user}
		<div style="margin: 1rem;">
		  <button on:click={login}>Login</button>
		</div>
	  {/if}
  
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
				{#if getImageUrl(article)}
				  <img 
					src={getImageUrl(article)} 
					alt={article.headline?.main || 'Article image'}
					on:error={(e) => {
					  e.target.style.display = 'none';
					}}
				  />
				{:else}
				  <div style="height: 150px; background: #eee; display: flex; align-items: center; justify-content: center;">
					<span>No image available</span>
				  </div>
				{/if}
			  </div>
			  <h2 class="article-title">{article.headline?.main || 'No title available'}</h2>
			  <p class="article-date">
				{#if article.pub_date}
				  {new Date(article.pub_date).toLocaleDateString('en-US', {
					weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
				  })}
				{:else}
				  Date unavailable
				{/if}
			  </p>
			  <p class="article-snippet">{article.snippet || 'No snippet available'}</p>
			</article>
		  </a>
  
		  <div style="padding: 10px 0;" class="article-body">
			<h4>Comments:</h4>
  
			{#if commentLists[article.web_url]?.length > 0}
			  <ul>
				{#each commentLists[article.web_url] as c}
				  <li style="margin-bottom: 8px;">
					<strong>{c.author_email}</strong>
					<em> ({new Date(c.timestamp).toLocaleString()})</em><br>
					{c.text}
					{#if isModerator}
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
