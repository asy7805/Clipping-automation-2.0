import { useState, useEffect } from 'react';

export const useTimezone = () => {
  const [timezone, setTimezone] = useState(() => 
    localStorage.getItem('user_timezone') || Intl.DateTimeFormat().resolvedOptions().timeZone
  );

  useEffect(() => {
    localStorage.setItem('user_timezone', timezone);
  }, [timezone]);

  const formatDateTime = (dateString: string) => {
    try {
      const date = new Date(dateString);
      return new Intl.DateTimeFormat('en-US', {
        timeZone: timezone,
        dateStyle: 'medium',
        timeStyle: 'short'
      }).format(date);
    } catch (e) {
      console.error("Error formatting date:", e);
      return dateString;
    }
  };

  return { timezone, setTimezone, formatDateTime };
};

