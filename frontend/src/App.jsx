import { useState, useEffect } from 'react';
import { MantineProvider } from '@mantine/core';
import { BrowserRouter, Routes, Route, Navigate, useParams, useNavigate } from 'react-router-dom';
import { Auth } from './Auth';
import { Lobby } from './Lobby';
import { GameRoom } from './GameRoom';
import { checkLogin, logout } from './api';

import '@mantine/core/styles.css';

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const verifyUser = async () => {
      try {
        const loggedInUser = await checkLogin();
        setUser(loggedInUser);
      } catch {
        setUser(null);
      } finally {
        setLoading(false);
      }
    };
    verifyUser();
  }, []);

  const handleLogin = (loggedInUser) => {
    setUser(loggedInUser);
  };

  const handleLogout = async () => {
    await logout();
    setUser(null);
  };

  if (loading) {
    return <div>Loading...</div>;
  }

  return (
    <MantineProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={
            user ? <Navigate to="/" /> : <Auth onLogin={handleLogin} />
          } />
          <Route path="/" element={
            user ? <Lobby username={user.username} onLogout={handleLogout} /> : <Navigate to="/login" />
          } />
          <Route path="/game/:gameCode" element={
            user ? <GameRoomWrapper username={user.username} /> : <Navigate to="/login" />
          } />
        </Routes>
      </BrowserRouter>
    </MantineProvider>
  );
}

// Wrapper component to extract params and pass them to GameRoom
const GameRoomWrapper = ({ username }) => {
  const { gameCode } = useParams();
  const navigate = useNavigate();

  const handleLeave = () => {
    navigate('/');
  }
  return <GameRoom gameCode={gameCode} username={username} onLeave={handleLeave} />;
};


export default App;
