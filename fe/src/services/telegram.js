// In production, these should NOT be exposed directly in the React frontend.
// This is done here per the implementation requirements for the hackathon prototype.

// Fallback tokens if not set in environment (since it's a hackathon demo)
const BOT_TOKEN = import.meta.env.VITE_TELEGRAM_BOT_TOKEN || 'YOUR_BOT_TOKEN_HERE';
const DEFAULT_CHAT_ID = import.meta.env.VITE_TELEGRAM_CHAT_ID || 'YOUR_CHAT_ID_HERE';

/**
 * Sends a message via the Telegram Bot API.
 * @param {string} text - The message to send.
 * @param {string} [chatId] - The target chat_id. Defaults to env config.
 */
export const sendTelegramMessage = async (text, chatId = DEFAULT_CHAT_ID) => {
  if (BOT_TOKEN === 'YOUR_BOT_TOKEN_HERE') {
    console.warn('Telegram Bot Token is not set. Skipping actual send.');
    return { ok: false, description: 'Token not configured' };
  }

  const url = `https://api.telegram.org/bot${BOT_TOKEN}/sendMessage`;

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        chat_id: chatId,
        text: text,
      }),
    });
    
    if (!response.ok) {
      throw new Error(`Telegram API Error: ${response.statusText}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error sending message:', error);
    throw error;
  }
};
