export function getPlayerHeadshot(playerId) {
  if (!playerId) return "";
  return `https://cdn.nba.com/headshots/nba/latest/1040x760/${playerId}.png`;
}

export function getTeamLogo(teamId) {
  if (!teamId) return "";
  return `https://cdn.nba.com/logos/nba/${teamId}/global/L/logo.svg`;
}