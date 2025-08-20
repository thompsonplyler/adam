import { MantineProvider } from '@mantine/core';
import { BrowserRouter, Routes, Route, useParams, useNavigate } from 'react-router-dom';
import HomePage from './HomePage'; // Import the new home page
import { GameRoom } from './GameRoom';

import '@mantine/core/styles.css';

function App() {
  return (
    <MantineProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/game/:gameCode" element={<GameRoomWrapper />} />
        </Routes>
      </BrowserRouter>
    </MantineProvider>
  );
}

// Wrapper component to extract params and pass them to GameRoom
// We'll need to adjust this to not rely on a user prop soon
const GameRoomWrapper = () => {
  const { gameCode } = useParams();
  const navigate = useNavigate();

  const handleLeave = () => {
    navigate('/');
  }
  // The username will need to come from somewhere else, like session storage or a join-game flow
  return <GameRoom gameCode={gameCode} username="TestPlayer" onLeave={handleLeave} />;
};


export default App;
