'use client';

import { useState, useEffect } from 'react';

export default function Home() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [message, setMessage] = useState('');
  const [userRole, setUserRole] = useState('');

  const [posts, setPosts] = useState<any[]>([]);
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    const res = await fetch('/api/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    const data = await res.json();
    if (res.ok) {
      setUserRole(data.role);
      fetchPosts();
    } else {
      setMessage(data.error || 'Login Failed');
    }
  };

  const fetchPosts = async () => {
    const res = await fetch('/api/board');
    const data = await res.json();
    setPosts(data);
  };

  const handleWrite = async (e: React.FormEvent) => {
    e.preventDefault();
    const res = await fetch('/api/board', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, content, author: userRole }),
    });
    
    if (res.ok) {
      setTitle('');
      setContent('');
      fetchPosts();
    } else {
      alert('Failed to write post');
    }
  };

  if (userRole) {
    return (
      <div style={{ padding: '40px', fontFamily: 'sans-serif', maxWidth: '800px', margin: '0 auto' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h1 style={{ color: userRole === 'admin' ? 'red' : 'blue' }}>
            Welcome, {userRole.toUpperCase()}!
          </h1>
          <button onClick={() => window.location.reload()} style={{ padding: '5px 10px' }}>Logout</button>
        </div>

        {userRole === 'admin' && <p style={{background: '#ffebee', padding: '10px'}}>🚩 Flag: DO_NOT_SHARE_THIS_FLAG</p>}

        <hr />
        
        {/* 글쓰기 폼 */}
        <h3>📝 Write a Post</h3>
        <form onSubmit={handleWrite} style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '30px' }}>
          <input 
            type="text" placeholder="Title" value={title} onChange={(e) => setTitle(e.target.value)} 
            style={{ padding: '10px', border: '1px solid #ddd' }} required 
          />
          <textarea 
            placeholder="Content" value={content} onChange={(e) => setContent(e.target.value)} 
            style={{ padding: '10px', border: '1px solid #ddd', height: '80px' }} required 
          />
          <button type="submit" style={{ padding: '10px', background: '#333', color: '#fff', border: 'none', cursor: 'pointer' }}>
            Post
          </button>
        </form>

        {/* 게시글 목록 */}
        <h3>📋 Board List</h3>
        <div style={{ background: '#f9f9f9', border: '1px solid #eee', padding: '20px' }}>
          {posts.map((post) => (
            <div key={post.id} style={{ borderBottom: '1px solid #ddd', padding: '10px 0' }}>
              <div style={{ fontWeight: 'bold', fontSize: '1.1em' }}>{post.title}</div>
              <div style={{ color: '#666', fontSize: '0.9em', marginBottom: '5px' }}>
                Author: <span style={{ color: post.author === 'admin' ? 'red' : 'blue' }}>{post.author}</span>
              </div>
              <div>{post.content}</div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', background: '#f0f2f5' }}>
      <form onSubmit={handleLogin} style={{ background: 'white', padding: '40px', borderRadius: '10px', boxShadow: '0 4px 6px rgba(0,0,0,0.1)' }}>
        <h2 style={{ textAlign: 'center', marginBottom: '20px' }}>Secure Login</h2>
        <input
          type="text" placeholder="Username" value={username} onChange={(e) => setUsername(e.target.value)}
          style={{ display: 'block', width: '200px', padding: '10px', marginBottom: '10px' }}
        />
        <input
          type="password" placeholder="Password" value={password} onChange={(e) => setPassword(e.target.value)}
          style={{ display: 'block', width: '200px', padding: '10px', marginBottom: '20px' }}
        />
        <button type="submit" style={{ width: '100%', padding: '10px', background: '#0070f3', color: 'white', border: 'none', borderRadius: '5px', cursor: 'pointer' }}>
          Login
        </button>
        {message && <p style={{ color: 'red', marginTop: '10px', textAlign: 'center' }}>{message}</p>}
      </form>
    </div>
  );
}
