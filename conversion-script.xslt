<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="2.0" xpath-default-namespace="http://www.tei-c.org/ns/1.0" xmlns:tei="http://www.tei-c.org/ns/1.0">

  <xsl:variable name="witness-id"><xsl:value-of select="/TEI/teiHeader/fileDesc/sourceDesc/msDesc/msIdentifier/@xml:id"/></xsl:variable>

  <xsl:output method="text" indent="no"/>
  <xsl:strip-space elements="div"/>
  <xsl:template match="text()">
    <!--  <xsl:value-of select="replace(., '\s+', ' ')"/>-->
      <xsl:value-of select="normalize-space(.)"/>
  </xsl:template>

  <xsl:template match="/">
    {witness:<xsl:value-of select="$witness-id"/>}
    {content:<xsl:apply-templates select="//body"/>}
  </xsl:template>

  <xsl:template match="div//head"><xsl:apply-templates/></xsl:template>

  <xsl:template match="p">
    <xsl:text>&#xa;</xsl:text>
    <xsl:apply-templates />
    <xsl:text>&#xa;</xsl:text>
  </xsl:template>

  <xsl:template match="tei:lb">
    <xsl:choose>
      <xsl:when test="@break='no'">
        <xsl:text></xsl:text></xsl:when>
      <xsl:otherwise><xsl:text> </xsl:text></xsl:otherwise>
    </xsl:choose>
  </xsl:template>


  <xsl:template match="unclear">{unclear:<xsl:apply-templates/>}</xsl:template>

  <xsl:template match="hi">
    <xsl:if test="@rend='initial'">
    {initial:
    </xsl:if>
    <xsl:if test="@rend='ekthesis'">
      {ekthesis:
    </xsl:if>
    <xsl:if test="@rend='overline'">
    {overline:
  </xsl:if>
  <xsl:apply-templates/>}
  </xsl:template>


  <xsl:template match="pb">
    <xsl:choose>
      <xsl:when test="@break='no'">
        {f:<xsl:value-of select="./@n"/>}</xsl:when>
      <xsl:otherwise><xsl:text> </xsl:text>{f:<xsl:value-of select="./@n"/>}<xsl:text> </xsl:text></xsl:otherwise>
    </xsl:choose>
  </xsl:template>

  <xsl:template match="del">
    <xsl:text> </xsl:text>
    {del:<xsl:apply-templates/><xsl:text>, </xsl:text><xsl:value-of select="@rend"/>}
    <xsl:text> </xsl:text>
  </xsl:template>

  <xsl:template match="add">
    <xsl:text> </xsl:text>
    {add:<xsl:apply-templates/><xsl:text>, </xsl:text><xsl:value-of select="@place"/>}
    <xsl:text> </xsl:text>
  </xsl:template>

  <xsl:template match="tei:gap">
    <xsl:text> </xsl:text>
    {gap:<xsl:value-of select="@quantity"/><xsl:text> </xsl:text><xsl:value-of select="@unit"/>}
    <xsl:text> </xsl:text>
  </xsl:template>

  <xsl:template match="tei:choice">
		<xsl:text> (</xsl:text>
		<xsl:value-of select="tei:expan"/>
		<xsl:text>) </xsl:text>
	</xsl:template>

<xsl:template match="g">
  <xsl:if test="@type='doubled_diple'">
    <xsl:text>» </xsl:text>
  </xsl:if>
  <xsl:if test="@type='diple'">
    <xsl:text>› </xsl:text>
  </xsl:if>
</xsl:template>

<xsl:template match="note">
</xsl:template>

</xsl:stylesheet>
