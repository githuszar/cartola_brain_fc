#!/usr/bin/env python3
"""
FantasyBrain V1.0 - Script de Sincronização

Script principal para coletar e armazenar dados do Cartola FC.

Uso:
    python sync.py              # Sincroniza rodada atual
    python sync.py --rodada 5   # Sincroniza rodada específica
    python sync.py --force      # Ignora cache
    python sync.py --status     # Mostra status do mercado
    python sync.py --stats      # Mostra estatísticas do banco
"""

import argparse
import sys
from datetime import datetime


def mostrar_status():
    """Mostra o status atual do mercado do Cartola FC"""
    from cartola_service import CartolaService

    print("=" * 60)
    print("FANTASYBRAIN V1.0 - STATUS DO MERCADO")
    print("=" * 60)

    service = CartolaService()
    status = service.fetch_mercado_status(use_cache=False)

    if not status:
        print("\n❌ Erro ao obter status do mercado")
        return

    rodada = status.get("rodada_atual", "?")
    status_mercado = status.get("status_mercado", 0)
    times_escalados = status.get("times_escalados", 0)
    fechamento = status.get("fechamento", {})

    status_texto = {
        1: "🟢 Aberto (pode escalar)",
        2: "🔴 Fechado (jogos em andamento)",
        3: "🟡 Fim de rodada (aguardando abertura)"
    }

    print(f"\n📅 Rodada atual: {rodada}")
    print(f"📊 Status: {status_texto.get(status_mercado, 'Desconhecido')}")
    print(f"👥 Times escalados: {times_escalados:,}")

    if fechamento:
        dia = fechamento.get("dia", "?")
        mes = fechamento.get("mes", "?")
        hora = fechamento.get("hora", "?")
        minuto = fechamento.get("minuto", "?")
        print(f"⏰ Fechamento: {dia}/{mes} às {hora}:{minuto:02d}")

    print("=" * 60)


def mostrar_estatisticas():
    """Mostra estatísticas do banco de dados local"""
    from database import get_stats, DB_PATH

    print("=" * 60)
    print("FANTASYBRAIN V1.0 - ESTATÍSTICAS DO BANCO")
    print("=" * 60)
    print(f"\n📁 Arquivo: {DB_PATH}")

    stats = get_stats()

    print(f"\n📊 Registros por tabela:")
    print(f"   • Clubes: {stats.get('clubes', 0)}")
    print(f"   • Jogadores: {stats.get('jogadores', 0)}")
    print(f"   • Partidas: {stats.get('partidas', 0)}")
    print(f"   • Pontuações: {stats.get('pontuacoes_jogadores', 0)}")
    print(f"   • Scouts: {stats.get('scouts_jogadores', 0)}")
    print(f"   • Histórico jogadores: {stats.get('historico_jogadores', 0)}")
    print(f"   • Histórico mercado: {stats.get('historico_mercado_status', 0)}")
    print(f"   • Calendário: {stats.get('calendario', 0)}")

    rodadas = stats.get("rodadas_com_dados", [])
    if rodadas:
        print(f"\n📅 Rodadas com dados: {', '.join(map(str, rodadas))}")

    print(f"\n🕐 Última atualização: {stats.get('ultima_atualizacao', 'Nunca')}")
    print("=" * 60)


def mostrar_jogadores_top():
    """Mostra os jogadores com melhor média"""
    from database import get_connection, POSICOES

    print("=" * 60)
    print("FANTASYBRAIN V1.0 - TOP JOGADORES")
    print("=" * 60)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT apelido, clube, posicao_id, preco, media_pontos, status_id
        FROM jogadores
        WHERE status_id = 7
        ORDER BY media_pontos DESC
        LIMIT 15
    """)

    print(f"\n{'Jogador':<20} {'Clube':<10} {'Pos':<8} {'Preço':<8} {'Média':<6}")
    print("-" * 60)

    for row in cursor.fetchall():
        nome = row[0][:19] if row[0] else "?"
        clube = (row[1] or "?")[:9]
        pos = POSICOES.get(row[2], "?")[:7]
        preco = row[3] or 0
        media = row[4] or 0

        print(f"{nome:<20} {clube:<10} {pos:<8} C${preco:<6.1f} {media:<6.1f}")

    conn.close()
    print("=" * 60)


def sincronizar(rodada=None, force=False, extras=False):
    """Executa a sincronização de dados"""
    from cartola_service import sincronizar as sync_cartola
    return sync_cartola(rodada, force, extras)


def main():
    parser = argparse.ArgumentParser(
        description="FantasyBrain V1.0 - Sincronização de dados do Cartola FC",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python sync.py              # Sincroniza rodada atual
  python sync.py --rodada 5   # Sincroniza rodada específica
  python sync.py --force      # Ignora cache, busca dados frescos
  python sync.py --status     # Mostra status do mercado
  python sync.py --stats      # Mostra estatísticas do banco
  python sync.py --top        # Mostra top jogadores
        """
    )

    parser.add_argument(
        "--rodada", "-r",
        type=int,
        help="Rodada específica para sincronizar"
    )

    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Ignorar cache e buscar dados frescos"
    )

    parser.add_argument(
        "--extras",
        action="store_true",
        help="Sincronizar endpoints extras (posicoes, rodadas, destaques, rankings, mercado_destaques)"
    )

    parser.add_argument(
        "--status", "-s",
        action="store_true",
        help="Mostrar status do mercado"
    )

    parser.add_argument(
        "--stats",
        action="store_true",
        help="Mostrar estatísticas do banco de dados"
    )

    parser.add_argument(
        "--top", "-t",
        action="store_true",
        help="Mostrar top jogadores"
    )

    args = parser.parse_args()

    # Executar ação correspondente
    if args.status:
        mostrar_status()
    elif args.stats:
        mostrar_estatisticas()
    elif args.top:
        mostrar_jogadores_top()
    else:
        resultado = sincronizar(args.rodada, args.force, extras=args.extras)
        if not resultado.get("sucesso"):
            sys.exit(1)


if __name__ == "__main__":
    main()
