import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Plus } from "lucide-react";

const VideoEditorProjects = () => {
  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold mb-2">Video Editor Projects</h1>
          <p className="text-muted-foreground">Create and manage your video editing projects</p>
        </div>
        <Button variant="hero">
          <Plus className="w-4 h-4 mr-2" />
          New Project
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <Card className="p-6 hover:shadow-lg transition-shadow cursor-pointer">
          <h3 className="font-semibold mb-2">Project Placeholder</h3>
          <p className="text-sm text-muted-foreground">Video editor feature coming soon</p>
        </Card>
      </div>
    </div>
  );
};

export default VideoEditorProjects;
