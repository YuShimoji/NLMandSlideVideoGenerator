using NLMSlidePlugin.Core;
using Xunit;

namespace NLMSlidePlugin.Tests
{
    public class VoiceSpeakerMappingTests
    {
        [Fact]
        public void CreateDefault_ReturnsNonEmptyMapping()
        {
            var mapping = VoiceSpeakerMapping.CreateDefault();
            Assert.True(mapping.Count > 0);
        }

        [Theory]
        [InlineData("れいむ", "YukkuriVoice", "reimu")]
        [InlineData("まりさ", "YukkuriVoice", "marisa")]
        [InlineData("Reimu", "YukkuriVoice", "reimu")]
        [InlineData("Speaker1", "YukkuriVoice", "reimu")]
        [InlineData("Speaker2", "YukkuriVoice", "marisa")]
        [InlineData("ずんだもん", "YukkuriVoice", "reimu")]
        public void Resolve_KnownSpeaker_ReturnsCorrectMapping(string speakerName, string expectedApi, string expectedId)
        {
            var mapping = VoiceSpeakerMapping.CreateDefault();
            var result = mapping.Resolve(speakerName);

            Assert.Equal(expectedApi, result.Api);
            Assert.Equal(expectedId, result.Id);
        }

        [Theory]
        [InlineData("UnknownSpeaker")]
        [InlineData("")]
        [InlineData(null)]
        public void Resolve_UnknownOrEmpty_ReturnsDefault(string? speakerName)
        {
            var mapping = VoiceSpeakerMapping.CreateDefault();
            var result = mapping.Resolve(speakerName!);
            var defaultSpeaker = VoiceSpeakerMapping.DefaultSpeaker;

            Assert.Equal(defaultSpeaker.Api, result.Api);
            Assert.Equal(defaultSpeaker.Id, result.Id);
        }

        [Fact]
        public void HasMapping_KnownSpeaker_ReturnsTrue()
        {
            var mapping = VoiceSpeakerMapping.CreateDefault();
            Assert.True(mapping.HasMapping("れいむ"));
            Assert.True(mapping.HasMapping("Speaker1"));
        }

        [Fact]
        public void HasMapping_UnknownSpeaker_ReturnsFalse()
        {
            var mapping = VoiceSpeakerMapping.CreateDefault();
            Assert.False(mapping.HasMapping("UnknownSpeaker"));
            Assert.False(mapping.HasMapping(""));
            Assert.False(mapping.HasMapping(null!));
        }

        [Fact]
        public void Resolve_CaseInsensitive()
        {
            var mapping = VoiceSpeakerMapping.CreateDefault();
            var lower = mapping.Resolve("reimu");
            var upper = mapping.Resolve("REIMU");
            var mixed = mapping.Resolve("Reimu");

            Assert.Equal(lower.Api, upper.Api);
            Assert.Equal(lower.Id, upper.Id);
            Assert.Equal(lower.Api, mixed.Api);
            Assert.Equal(lower.Id, mixed.Id);
        }

        [Fact]
        public void DefaultSpeaker_IsYukkuriReimu()
        {
            var defaultSpeaker = VoiceSpeakerMapping.DefaultSpeaker;
            Assert.Equal("YukkuriVoice", defaultSpeaker.Api);
            Assert.Equal("reimu", defaultSpeaker.Id);
        }

        [Fact]
        public void VoiceSpeakerId_RecordEquality()
        {
            var a = new VoiceSpeakerId("YukkuriVoice", "reimu");
            var b = new VoiceSpeakerId("YukkuriVoice", "reimu");
            Assert.Equal(a, b);

            var c = new VoiceSpeakerId("YukkuriVoice", "marisa");
            Assert.NotEqual(a, c);
        }
    }
}
