import { useState, useEffect, useRef } from "react";

interface UseAutoSaveOptions {
  interval?: number; // milliseconds
  debounceMs?: number; // milliseconds
}

export function useAutoSave(
  projectId: string,
  editState: any,
  saveFunction: () => Promise<void>,
  options: UseAutoSaveOptions = {}
) {
  const { interval = 30000, debounceMs = 1000 } = options;
  const [isSaving, setIsSaving] = useState(false);
  const [lastSaved, setLastSaved] = useState<string | null>(null);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  
  const saveTimeoutRef = useRef<NodeJS.Timeout>();
  const lastSavedStateRef = useRef<any>();

  // Check if edit state has changed
  useEffect(() => {
    if (!editState) return;
    
    const hasChanged = JSON.stringify(editState) !== JSON.stringify(lastSavedStateRef.current);
    setHasUnsavedChanges(hasChanged);
    
    if (hasChanged) {
      // Clear existing timeout
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
      }
      
      // Set new timeout for debounced save
      saveTimeoutRef.current = setTimeout(() => {
        performSave();
      }, debounceMs);
    }
    
    return () => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
      }
    };
  }, [editState, debounceMs]);

  // Auto-save on interval
  useEffect(() => {
    if (!hasUnsavedChanges) return;
    
    const intervalId = setInterval(() => {
      performSave();
    }, interval);
    
    return () => clearInterval(intervalId);
  }, [interval, hasUnsavedChanges]);

  const performSave = async () => {
    if (!hasUnsavedChanges || isSaving) return;
    
    try {
      setIsSaving(true);
      await saveFunction();
      
      lastSavedStateRef.current = editState;
      setHasUnsavedChanges(false);
      setLastSaved(new Date().toLocaleTimeString());
    } catch (error) {
      console.error("Auto-save failed:", error);
    } finally {
      setIsSaving(false);
    }
  };

  // Manual save function
  const saveNow = async () => {
    await performSave();
  };

  return {
    isSaving,
    lastSaved,
    hasUnsavedChanges,
    saveNow
  };
}







