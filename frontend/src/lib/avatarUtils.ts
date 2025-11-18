/**
 * Generate a consistent color for a channel name
 */
export function getChannelColor(channelName: string): string {
  const colors = [
    'from-blue-500 to-cyan-500',
    'from-purple-500 to-pink-500',
    'from-green-500 to-emerald-500',
    'from-orange-500 to-red-500',
    'from-indigo-500 to-purple-500',
    'from-rose-500 to-pink-500',
    'from-teal-500 to-cyan-500',
    'from-amber-500 to-orange-500',
  ];
  
  // Generate consistent index from channel name
  const hash = channelName.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
  return colors[hash % colors.length];
}

/**
 * Get channel initials (first 2 letters, uppercase)
 */
export function getChannelInitials(channelName: string): string {
  return channelName.slice(0, 2).toUpperCase();
}

/**
 * Generate avatar element for a channel
 */
export function getChannelAvatarProps(channelName: string) {
  return {
    gradient: getChannelColor(channelName),
    initials: getChannelInitials(channelName),
  };
}

