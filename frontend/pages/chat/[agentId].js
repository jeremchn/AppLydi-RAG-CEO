import { useRouter } from 'next/router';
import { useEffect } from 'react';

export default function AgentChat() {
  const router = useRouter();
  const { agentId } = router.query;

  useEffect(() => {
    // Redirect to main page with agentId parameter
    if (agentId) {
      router.push(`/?agentId=${agentId}`);
    }
  }, [agentId, router]);

  return (
    <div style={{ padding: '20px', textAlign: 'center' }}>
      <p>Redirection vers l'agent...</p>
    </div>
  );
}