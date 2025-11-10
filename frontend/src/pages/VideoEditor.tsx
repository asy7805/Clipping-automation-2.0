import { useParams } from "react-router-dom";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ArrowLeft } from "lucide-react";
import { useNavigate } from "react-router-dom";

const VideoEditor = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <Button
          variant="ghost"
          onClick={() => navigate("/dashboard/editor/projects")}
          className="mb-4"
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Projects
        </Button>
        <h1 className="text-3xl font-bold mb-2">Video Editor</h1>
        <p className="text-muted-foreground">Project ID: {projectId}</p>
      </div>

      <Card className="p-8">
        <div className="text-center py-12">
          <h2 className="text-2xl font-semibold mb-4">Video Editor Feature</h2>
          <p className="text-muted-foreground mb-6">
            The video editor interface is coming soon. This is a placeholder component.
          </p>
        </div>
      </Card>
    </div>
  );
};

export default VideoEditor;
